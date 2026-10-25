#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=================================================="
echo "    UPGRADING NOVA TITAN ENGINE (Nova Studio 24)"
echo "=================================================="

# ১. আগের চলমান ইঞ্জিন প্রসেস বন্ধ করা
echo "[+] Stopping any running engine instances..."
pkill -f llama-server || true
pkill -f engine_bridge.py || true

# ২. গিটহাব থেকে লেটেস্ট কোড ও আপডেট নামানো
echo "[+] Pulling latest updates from GitHub..."
git reset --hard HEAD
git pull origin main

# ৩. পারমিশন ঠিক করা
echo "[+] Updating file permissions..."
chmod +x setup.sh run_engine.sh upgrade.sh

# ৪. পাইথন ডিপেন্ডেন্সি আপডেট
echo "[+] Checking Python libraries..."
pip install --upgrade requests firebase-admin

# ৫. শর্টকাট কমান্ড সেট করা (যাতে যেকোনো জায়গা থেকে 'upgrade-ai' লিখলেই কাজ হয়)
SHORTCUT_PATH="/data/data/com.termux/files/usr/bin/upgrade-ai"
CURRENT_DIR=$(pwd)

cat << 'EOF' > "$SHORTCUT_PATH"
#!/data/data/com.termux/files/usr/bin/bash
cd CURRENT_DIR_PLACEHOLDER && bash upgrade.sh
EOF

sed -i "s|CURRENT_DIR_PLACEHOLDER|$CURRENT_DIR|g" "$SHORTCUT_PATH"
chmod +x "$SHORTCUT_PATH"

echo "=================================================="
echo " [SUCCESS] Nova Titan Engine successfully updated!"
echo " Shortcut created: Type 'upgrade-ai' anytime to update."
echo " To start the engine now, run: bash run_engine.sh"
echo "=================================================="
