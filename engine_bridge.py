import os
import time
import json
import requests

# ==========================================
# ১. ডুয়াল পোর্ট ও ফায়ারবেস কনফিগারেশন
# ==========================================
TITAN_ENGINE_URL = "http://127.0.0.1:8080/v1/chat/completions" # Port 8080 (7B Pro)
SPARK_ENGINE_URL = "http://127.0.0.1:8081/v1/chat/completions" # Port 8081 (1.5B Rapid)

# আপনার ফায়ারবেস রিয়েলটাইম ডেটাবেস লিংক (শেষে স্ল্যাশ ছাড়া)
FIREBASE_DB_URL = "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"

# প্রম্পট লোড
if os.path.exists("system_prompt.txt"):
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        TITAN_SYSTEM_PROMPT = f.read()
else:
    TITAN_SYSTEM_PROMPT = "You are Nova Titan Coder by Nova Studio 24."

if os.path.exists("system_prompt_spark.txt"):
    with open("system_prompt_spark.txt", "r", encoding="utf-8") as f:
        SPARK_SYSTEM_PROMPT = f.read()
else:
    SPARK_SYSTEM_PROMPT = "You are Nova Spark, high-speed coding assistant by Nova Studio 24."

# ==========================================
# ২. অ্যাডমিন প্যানেল টোকেন কন্ট্রোল
# ==========================================
def get_admin_token_limit():
    try:
        res = requests.get(f"{FIREBASE_DB_URL}/admin/settings/max_tokens.json", timeout=5)
        if res.status_code == 200 and res.text != 'null':
            return int(res.json())
    except Exception:
        pass
    return 2048

# ==========================================
# ৩. মালিক ও গেস্ট কোড ভ্যালিডেশন
# ==========================================
def verify_access_and_credits(user_id, prompt_text, session_token=None):
    try:
        user_res = requests.get(f"{FIREBASE_DB_URL}/users/{user_id}.json", timeout=5)
        user_data = user_res.json() if user_res.status_code == 200 and user_res.text != 'null' else {}

        # ১. মাস্টার কোড দিয়ে মালিকানা আনলক
        MASTER_SECRET = "#OWNER-BOSS-999"
        if MASTER_SECRET in prompt_text:
            requests.patch(f"{FIREBASE_DB_URL}/users/{user_id}.json", json={
                "role": "owner",
                "unlimited": True,
                "credits": 999999999
            }, timeout=5)
            return True, "owner", True

        if user_data.get("role") == "owner" or user_data.get("unlimited") == True:
            return True, "owner", False

        # ২. গেস্ট কোড চেক
        if session_token:
            v_res = requests.get(f"{FIREBASE_DB_URL}/vouchers/{session_token}.json", timeout=5)
            if v_res.status_code == 200 and v_res.text != 'null':
                v_data = v_res.json()
                if v_data.get("valid") == True:
                    return True, "guest_unlimited", False

        # ৩. সাধারণ ক্রেডিট চেক
        credits = user_data.get("credits", 5)
        if credits > 0:
            requests.patch(f"{FIREBASE_DB_URL}/users/{user_id}.json", json={"credits": credits - 1}, timeout=5)
            return True, "regular_user", False
        else:
            return False, "exhausted", False

    except Exception:
        return True, "offline_user", False

# ==========================================
# ৪. এআই মডেল কল (সঠিক পোর্টে রাউট করা)
# ==========================================
def dispatch_to_ai(selected_model, prompt, is_owner, max_tokens):
    if selected_model.lower() == "spark":
        target_url = SPARK_ENGINE_URL
        system_instruction = SPARK_SYSTEM_PROMPT
        model_name = "nova-spark-1.5b"
    else:
        target_url = TITAN_ENGINE_URL
        system_instruction = TITAN_SYSTEM_PROMPT
        model_name = "nova-titan-7b"

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
# ৫. মূল ফায়ারবেস লিসেনার লুপ (REST API)
# ==========================================
def start_router():
    print("[*] Nova Studio 24 REST Router is actively listening to Firebase...")
    while True:
        try:
            res = requests.get(f"{FIREBASE_DB_URL}/requests/pending.json", timeout=10)
            if res.status_code == 200 and res.text != 'null':
                requests_list = res.json()
                if isinstance(requests_list, dict):
                    for req_id, data in requests_list.items():
                        user_id = data.get("user_id")
                        prompt = data.get("prompt")
                        model = data.get("model", "titan")
                        guest_code = data.get("guest_code", None)

                        print(f"[>] Routing request: {req_id} -> Target: {model.upper()}")

                        allowed, role, is_owner = verify_access_and_credits(user_id, prompt, guest_code)

                        if not allowed:
                            output = "⚠️ আপনার মেসেজ লিমিট শেষ! আনলিমিটেড অ্যাক্সেস পেতে রিডিম কোড দিন বা ক্রেডিট রিচার্জ করুন।"
                        else:
                            token_limit = get_admin_token_limit()
                            output = dispatch_to_ai(model, prompt, is_owner, token_limit)

                        # সম্পন্ন করে ফায়ারবেসে পাঠানো
                        requests.put(f"{FIREBASE_DB_URL}/requests/completed/{req_id}.json", json={
                            "user_id": user_id,
                            "response": output,
                            "engine_used": model,
                            "status": "done",
                            "timestamp": int(time.time())
                        }, timeout=5)

                        # পেন্ডিং থেকে ডিলিট
                        requests.delete(f"{FIREBASE_DB_URL}/requests/pending/{req_id}.json", timeout=5)
                        print(f"[✔] Request {req_id} served successfully!")

        except Exception:
            time.sleep(2)
            continue

        time.sleep(1)

if __name__ == "__main__":
    start_router()
