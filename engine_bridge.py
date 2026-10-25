import os
import time
import json
import requests
import firebase_admin
from firebase_admin import credentials, db

# ==========================================
# 1. কনফিগারেশন ও সিস্টেম প্রম্পট লোড
# ==========================================
LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
FIREBASE_DB_URL = "YOUR_FIREBASE_DATABASE_URL"  # পরে আপনার ফায়ারবেস লিংক বসাবেন
SYSTEM_PROMPT_FILE = "system_prompt.txt"

# সিস্টেম প্রম্পট লোড করা
if os.path.exists(SYSTEM_PROMPT_FILE):
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        BASE_SYSTEM_PROMPT = f.read()
else:
    BASE_SYSTEM_PROMPT = "You are Nova Titan Coder by Nova Studio 24."

# ফায়ারবেস অ্যাডমিন ইনিশিয়ালাইজেশন
cred_path = "firebase_credentials.json"
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
else:
    print("[!] Warning: firebase_credentials.json not found. Waiting for setup...")

# ==========================================
# 2. অ্যাডমিন প্যানেল থেকে টোকেন সেটিং রিড করা
# ==========================================
def get_admin_token_settings():
    """অ্যাডমিন প্যানেলে আপনার সেট করা টোকেন লিমিট লাইভ ফেচ করবে"""
    try:
        settings_ref = db.reference('/admin/settings')
        settings = settings_ref.get()
        if settings and 'max_tokens' in settings:
            return int(settings['max_tokens'])
    except Exception as e:
        print(f"[-] Could not read admin settings: {e}")
    return 2048  # কোনো সেটিং না থাকলে ডিফল্ট ২০৪৮ টোকেন


# ==========================================
# 3. মাস্টার কোড ও ইউজার ভ্যালিডেশন
# ==========================================
def check_user_access(user_id, prompt_text):
    """মালিকের মাস্টার কোড ও সাধারণ ইউজারের ব্যালেন্স চেক"""
    try:
        user_ref = db.reference(f'/users/{user_id}')
        user_data = user_ref.get() or {}

        # আপনি যদি চ্যাটে মাস্টার কোড দেন, আপনাকে আজীবনের জন্য মালিক ঘোষণা করবে
        MASTER_CODE = "#OWNER-BOSS-999"
        if MASTER_CODE in prompt_text:
            user_ref.update({
                "role": "owner",
                "unlimited": True,
                "credits": 999999999
            })
            return True, "owner", True

        # আগের সেভ করা রোল চেক
        if user_data.get("role") == "owner" or user_data.get("unlimited") == True:
            return True, "owner", False

        # সাধারণ ইউজারের ক্রেডিট চেক
        current_credits = user_data.get("credits", 5)  # ফ্রিতে ৫টি চ্যাট
        if current_credits > 0:
            user_ref.update({"credits": current_credits - 1})
            return True, "user", False
        else:
            return False, "exhausted", False

    except Exception as e:
        print(f"[-] Auth Error: {e}")
        return True, "guest", False


# ==========================================
# 4. C++ Llama Engine-এ প্রম্পট পাঠানো
# ==========================================
def generate_ai_response(prompt, is_owner_trigger, max_tokens):
    system_instruction = BASE_SYSTEM_PROMPT
    
    # মালিকের গোপন কোড ব্যবহার করলে এআই-এর বিশেষ সালাম ও স্বীকারোক্তি
    if is_owner_trigger:
        system_instruction += "\n[ALERT: The user is your creator and owner of Nova Studio 24. Acknowledge him respectfully as Boss/Creator and confirm lifetime unlimited access.]"

    payload = {
        "model": "qwen2.5-coder-7b",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,  # অ্যাডমিন প্যানেল থেকে পাওয়া টোকেন লিমিট
        "temperature": 0.2         # কোডিং নিখুঁত হওয়ার জন্য কম তাপমাত্রা
    }

    try:
        res = requests.post(LLAMA_SERVER_URL, json=payload, timeout=120)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Engine Error: {str(e)}"
    
    return "Error: Could not generate response from Nova Titan Engine."


# ==========================================
# 5. ফায়ারবেস লুপ (রিয়েলটাইম মেসেজ হ্যান্ডলার)
# ==========================================
def start_engine_listener():
    print("[*] Nova Titan Engine Bridge is running and listening to Firebase...")
    
    while True:
        try:
            # পেন্ডিং রিকোয়েস্ট চেক
            requests_ref = db.reference('/requests/pending')
            pending_items = requests_ref.get()

            if pending_items:
                for req_id, req_data in pending_items.items():
                    user_id = req_data.get("user_id")
                    prompt = req_data.get("prompt")

                    print(f"[+] Processing request: {req_id} from user: {user_id}")

                    # ১. ইউজারের অধিকার ও ক্রেডিট চেক
                    allowed, role, is_owner = check_user_access(user_id, prompt)

                    if not allowed:
                        answer = "⚠️ আপনার চ্যাট ক্রেডিট শেষ হয়ে গেছে! অনুগ্রহ করে নতুন ক্রেডিট রিচার্জ করুন বা আনলিমিটেড কোড ব্যবহার করুন।"
                    else:
                        # ২. অ্যাডমিন প্যানেলে সেট করা টোকেন লোড করা
                        max_tokens = get_admin_token_settings()
                        # ৩. C++ এআই দিয়ে উত্তর তৈরি করা
                        answer = generate_ai_response(prompt, is_owner, max_tokens)

                    # ৪. উত্তর ফায়ারবেসে পাঠানো
                    db.reference(f'/requests/completed/{req_id}').set({
                        "user_id": user_id,
                        "response": answer,
                        "timestamp": int(time.time()),
                        "status": "done"
                    })

                    # পেন্ডিং লিস্ট থেকে রিকোয়েস্ট মুছে ফেলা
                    db.reference(f'/requests/pending/{req_id}').delete()
                    print(f"[✔] Request {req_id} completed successfully!")

        except Exception as err:
            time.sleep(2)
            continue

        time.sleep(1)

if __name__ == "__main__":
    start_engine_listener()
