#!/data/data/com.termux/files/usr/bin/bash

echo "=================================================="
echo "    STARTING NOVA TITAN ENGINE (Nova Studio 24)"
echo "=================================================="

# ১. স্ক্রিন অফ হলেও টারমাক্স যাতে ব্যাকগ্রাউন্ডে না মরে (Wake Lock)
if command -v termux-wake-lock &> /dev/null; then
    echo "[+] Enabling Termux Wake-Lock (CPU will stay active 24/7)..."
    termux-wake-lock
fi

# ২. মডেল এবং সার্ভার ফাইল চেক করা
MODEL_PATH="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
SERVER_BIN="llama.cpp/build/bin/llama-server"

if [ ! -f "$MODEL_PATH" ]; then
    echo "[-] Error: Model file not found! Run 'bash setup.sh' first."
    exit 1
fi

if [ ! -f "$SERVER_BIN" ]; then
    echo "[-] Error: llama-server binary not found! Compiling..."
    cd llama.cpp && cmake --build build --config Release -j$(nproc) && cd ..
fi

# ৩. সি++ Llama-Server ব্যাকগ্রাউন্ডে স্টার্ট করা (8K Context + 6 Threads)
echo "[+] Starting C++ Engine on Snapdragon CPU (Port 8080)..."
$SERVER_BIN \
    -m "$MODEL_PATH" \
    -c 8192 \
    -t 6 \
    --host 127.0.0.1 \
    --port 8080 > engine.log 2>&1 &

SERVER_PID=$!
echo "[+] C++ Llama Engine running with PID: $SERVER_PID"

# ৪. সার্ভার তৈরি হওয়া পর্যন্ত একটু অপেক্ষা
echo "[+] Waiting for C++ engine to initialize in RAM..."
sleep 6

# ৫. পাইথন ফায়ারবেস ব্রিজ রান করা
echo "[+] Starting Python Firebase Bridge..."
python engine_bridge.py &
BRIDGE_PID=$!
echo "[+] Firebase Bridge running with PID: $BRIDGE_PID"

echo "=================================================="
echo " [SUCCESS] Nova Titan Engine is LIVE and ONLINE!"
echo " Logs are saving to: engine.log"
echo " To stop the engine, press: CTRL + C"
echo "=================================================="

# স্ক্রিপ্ট বন্ধ করলে ক্লিন-আপ করার ব্যবস্থা
trap "echo '[!] Stopping Engine...'; kill $SERVER_PID $BRIDGE_PID; termux-wake-unlock; exit 0" SIGINT SIGTERM

# ইঞ্জিনকে একনাগাড়ে জীবন্ত রাখা
wait
