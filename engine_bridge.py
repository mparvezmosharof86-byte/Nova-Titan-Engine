import os
import time
import json
import requests
import firebase_admin
from firebase_admin import credentials, db

# ==========================================
# ১. ডুয়াল পোর্ট ও প্রম্পট কনফিগারেশন
# ==========================================
TITAN_ENGINE_URL = "http://127.0.0.1:8080/v1/chat/completions" # Port 8080 (7B Pro)
SPARK_ENGINE_URL = "http://127.0.0.1:8081/v1/chat/completions" # Port 8081 (1.5B Rapid)

FIREBASE_DB_URL = "YOUR_FIREBASE_DATABASE_URL"  # ফায়ারবেসের রিয়েলটাইম ডেটাবেস লিংক

# টাইটান প্রম্পট লোড
if os.path.exists("system_prompt.txt"):
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        TITAN_SYSTEM_PROMPT = f.read()
else:
    TITAN_SYSTEM_PROMPT = "You are Nova Titan Coder by Nova Studio 24."

# স্পার্ক প্রম্পট লোড
if os.path.exists("system_prompt_spark.txt"):
    with open("system_prompt_spark.txt", "r", encoding="utf-8") as f:
        SPARK_SYSTEM_PROMPT = f.read()
else:
    SPARK_SYSTEM_PROMPT = "You are Nova Spark, high-speed coding assistant by Nova Studio 24."

# ফায়ারবেস কানেকশন ইনিশিয়ালাইজ
cred_path = "firebase_credentials.json"
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
else:
    print("[!] Info: Place your 'firebase_credentials.json' here to connect Firebase.")

# ==========================================
# ২. অ্যাডমিন প্যানেল টোকেন কন্ট্রোল
# ==========================================
def get_admin_token_limit():
    """অ্যাডমিন প্যানেলে আপনার সেট করা টোকেন ডায়নামিক রিড করবে"""
    try:
        settings_ref = db.reference('/admin/settings/max_tokens')
        limit = settings_ref.get()
        if limit:
            return int(limit)
    except Exception:
        pass
    return 2048  # ডিফল্ট টোকেন লিমিট

# ==========================================
# ৩. মালিকের মাস্টার কোড ও গেস্ট কোড ভেরিফিকেশন
# ==========================================
def verify_access_and_credits(user_id, prompt_text, session_token=None):
    try:
        user_ref = db.reference(f'/users/{user_id}')
        user_data = user_ref.get() or {}

        # ১. মাস্টার কোড দিয়ে আজীবনের মালিকানা আনলক
        MASTER_SECRET = "#OWNER-BOSS-999"
        if MASTER_SECRET in prompt_text:
            user_ref.update({
                "role": "owner",
                "unlimited": True,
                "credits": 999999999
            })
            return True, "owner", True

        # আগের অ্যাক্টিভ মালিক চেক
        if user_data.get("role") == "owner" or user_data.get("unlimited") == True:
            return True, "owner", False

        # ২. গেস্ট কোড চেক (এক চ্যাটের জন্য আনলিমিটেড)
        if session_token:
            voucher_ref = db.reference(f'/vouchers/{session_token}')
            voucher = voucher_ref.get()
            if voucher and voucher.get("valid") == True:
                return True, "guest_unlimited", False

        # ৩. সাধারণ ইউজারের ফ্রি ব্যালেন্স চেক
        credits = user_data.get("credits", 5)
        if credits > 0:
            user_ref.update({"credits": credits - 1})
            return True, "regular_user", False
        else:
            return False, "exhausted", False

    except Exception as e:
        print(f"[-] Access check error: {e}")
        return True, "offline_user", False

# ==========================================
# ৪. স্মার্ট এআই কল (সঠিক পোর্টে মেসেজ রাউট করা)
# ==========================================
def dispatch_to_ai(selected_model, prompt, is_owner, max_tokens):
    # কোন মডেল সিলেক্ট করা হয়েছে তা নির্বাচন
    if selected_model.lower() == "spark":
        target_url = SPARK_ENGINE_URL
        system_instruction = SPARK_SYSTEM_PROMPT
        model_name = "nova-spark-1.5b"
    else:
        target_url = TITAN_ENGINE_URL
        system_instruction = TITAN_SYSTEM_PROMPT
        model_name = "nova-titan-7b"

    # মালিকের মেসেজ হলে বিশেষ অগ্রাধিকারের নির্দেশ
    if is_owner:
        system_instruction += "\n[SYSTEM ALERT: The user is your creator and master, Nova Studio 24 Boss. Address respectfully.]"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2
    }

    try:
        res = requests.post(target_url, json=payload, timeout=120)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
    except Exception as err:
        return f"Engine Error ({model_name}): {str(err)}"

    return "Error: Model did not respond."

# ==========================================
# ৫. মূল ফায়ারবেস লুপ (সার্ভিস প্রসেসর)
# ==========================================
def start_router():
    print("[*] Nova Studio 24 Router is actively listening to Firebase...")
    while True:
        try:
            pending_ref = db.reference('/requests/pending')
            requests_list = pending_ref.get()

            if requests_list:
                for req_id, data in requests_list.items():
                    user_id = data.get("user_id")
                    prompt = data.get("prompt")
                    model = data.get("model", "titan") # ডিফল্ট টাইটান
                    guest_code = data.get("guest_code", None)

                    print(f"[>] Routing request: {req_id} -> Target: {model.upper()}")

                    # ভেরিফিকেশন
                    allowed, role, is_owner = verify_access_and_credits(user_id, prompt, guest_code)

                    if not allowed:
                        output = "⚠️ আপনার মেসেজ লিমিট শেষ! আনলিমিটেড অ্যাক্সেস পেতে রিডিম কোড দিন বা ক্রেডিট রিচার্জ করুন।"
                    else:
                        token_limit = get_admin_token_limit()
                        output = dispatch_to_ai(model, prompt, is_owner, token_limit)

                    # রেজাল্ট ফেরত পাঠানো
                    db.reference(f'/requests/completed/{req_id}').set({
                        "user_id": user_id,
                        "response": output,
                        "engine_used": model,
                        "status": "done",
                        "timestamp": int(time.time())
                    })

                    # পেন্ডিং থেকে মুছে দেওয়া
                    pending_ref.child(req_id).delete()
                    print(f"[✔] Request {req_id} served via {model.upper()} successfully!")

        except Exception:
            time.sleep(2)
            continue

        time.sleep(1)

if __name__ == "__main__":
    start_router()
