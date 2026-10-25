#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=================================================="
echo "   NOVA DUAL-ENGINE SETUP (Nova Studio 24)"
echo "   1. Nova Titan (7B Heavy Pro Coder)"
echo "   2. Nova Spark (1.5B Rapid Planner)"
echo "=================================================="

# ১. টারমাক্স প্যাকেজ ও টুলস ইনস্টল
echo "[+] Updating Termux and installing base tools..."
pkg update -y && pkg upgrade -y
pkg install -y git cmake clang ninja python python-pip wget curl

# ২. পাইথনের লাইব্রেরি ইনস্টল (pip upgrade বাদ দিয়ে সেফ মোড)
echo "[+] Installing Python bridge dependencies..."
pip install requests firebase-admin --break-system-packages || pip install requests firebase-admin

# ৩. C++ Llama.cpp ক্লোন ও স্ন্যাপড্রাগনের জন্য বিল্ড
if [ ! -d "llama.cpp" ]; then
    echo "[+] Cloning llama.cpp repository..."
    git clone https://github.com/ggerganov/llama.cpp
fi

echo "[+] Compiling C++ llama-server with ARM64 / NEON optimizations..."
cd llama.cpp
cmake -B build -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF
cmake --build build --config Release -j$(nproc)
cd ..

# ৪. মডেল ফোল্ডার তৈরি
mkdir -p models

# ৫. মডেল ১: Nova Titan (7B Pro Coder) ডাউনলোড
TITAN_FILE="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
TITAN_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf"

if [ ! -f "$TITAN_FILE" ]; then
    echo "[+] Downloading Model 1: Nova Titan 7B (~4.6 GB)..."
    echo "[!] Full High-Power AI Model downloading via Wi-Fi..."
    wget -c "$TITAN_URL" -O "$TITAN_FILE"
else
    echo "[+] Model 1 (Nova Titan 7B) already exists!"
fi

# ৬. মডেল ২: Nova Spark (1.5B Rapid Coder) ডাউনলোড
SPARK_FILE="models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
SPARK_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"

if [ ! -f "$SPARK_FILE" ]; then
    echo "[+] Downloading Model 2: Nova Spark 1.5B (~980 MB)..."
    wget -c "$SPARK_URL" -O "$SPARK_FILE"
else
    echo "[+] Model 2 (Nova Spark 1.5B) already exists!"
fi

echo "=================================================="
echo " [SUCCESS] Both Titan (7B) & Spark (1.5B) are Ready!"
echo " Next run: bash run_engine.sh"
echo "=================================================="
