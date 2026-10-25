#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=================================================="
echo "   NOVA TITAN ENGINE (Nova Studio 24) SETUP"
echo "=================================================="

# ১. টারমাক্স প্যাকেজ আপডেট ও প্রয়োজনীয় টুলস ইনস্টল
echo "[+] Updating Termux and installing base tools..."
pkg update -y && pkg upgrade -y
pkg install -y git cmake clang ninja python wget curl

# ২. পাইথনের ফায়ারবেস ও রিকোয়েস্ট লাইব্রেরি ইনস্টল
echo "[+] Installing Python bridge dependencies..."
pip install --upgrade pip
pip install requests firebase-admin

# ৩. C++ Llama.cpp ক্লোন ও স্ন্যাপড্রাগন প্রসেসরের জন্য বিল্ড
if [ ! -d "llama.cpp" ]; then
    echo "[+] Cloning llama.cpp repository..."
    git clone https://github.com/ggerganov/llama.cpp
fi

echo "[+] Compiling C++ llama-server with ARM64 / NEON optimizations..."
cd llama.cpp
cmake -B build -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF
cmake --build build --config Release -j$(nproc)
cd ..

# ৪. মডেল রাখার জন্য ফোল্ডার তৈরি
mkdir -p models

# ৫. Qwen 2.5 Coder 7B (Q4_K_M) মডেল ডাউনলোড
MODEL_FILE="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf"

if [ ! -f "$MODEL_FILE" ]; then
    echo "[+] Downloading Qwen 2.5 Coder 7B Model (~4.6 GB)..."
    echo "[!] Download will resume automatically if disconnected."
    wget -c "$MODEL_URL" -O "$MODEL_FILE"
else
    echo "[+] Model already downloaded and ready: $MODEL_FILE"
fi

echo "=================================================="
echo " [SUCCESS] Nova Titan Engine setup complete!"
echo " Next run: bash run_engine.sh"
echo "=================================================="
