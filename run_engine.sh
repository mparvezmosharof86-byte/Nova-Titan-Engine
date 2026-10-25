#!/data/data/com.termux/files/usr/bin/bash

echo "=================================================="
echo "    STARTING NOVA DUAL-ENGINE (Nova Studio 24)"
echo "    1. Nova Titan  -> Port 8080 (7B Pro Coder)"
echo "    2. Nova Spark  -> Port 8081 (1.5B Rapid)"
echo "=================================================="

# ১. স্ক্রিন অফ হলেও প্রসেসর চালু রাখা (Wake Lock)
if command -v termux-wake-lock &> /dev/null; then
    echo "[+] Enabling Termux Wake-Lock (Active 24/7)..."
    termux-wake-lock
fi

TITAN_MODEL="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
SPARK_MODEL="models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
SERVER_BIN="llama.cpp/build/bin/llama-server"

# ২. ফাইল চেক
if [ ! -f "$TITAN_MODEL" ] || [ ! -f "$SPARK_MODEL" ]; then
    echo "[-] Error: One or both models missing! Run 'bash setup.sh' first."
    exit 1
fi

if [ ! -f "$SERVER_BIN" ]; then
    echo "[-] Error: llama-server binary not found! Compiling..."
    cd llama.cpp && cmake --build build --config Release -j$(nproc) && cd ..
fi

# ৩. ইঞ্জিন ১: Nova Titan চালু করা (Port 8080, 8K Context, 4 Threads)
echo "[+] Starting Engine 1: Nova Titan (Port 8080)..."
$SERVER_BIN \
    -m "$TITAN_MODEL" \
    -c 8192 \
    -t 4 \
    --host 127.0.0.1 \
    --port 8080 > titan.log 2>&1 &
TITAN_PID=$!

# ৪. ইঞ্জিন ২: Nova Spark চালু করা (Port 8081, 4K Context, 2 Threads)
echo "[+] Starting Engine 2: Nova Spark (Port 8081)..."
$SERVER_BIN \
    -m "$SPARK_MODEL" \
    -c 4096 \
    -t 2 \
    --host 127.0.0.1 \
    --port 8081 > spark.log 2>&1 &
SPARK_PID=$!

# ৫. সার্ভার দুটি মেমোরিতে লোড হওয়া পর্যন্ত সামান্য অপেক্ষা
echo "[+] Initializing both engines into RAM..."
sleep 6

# ৬. ফায়ারবেস কানেক্টর চালু করা
echo "[+] Starting Firebase Bridge Router..."
python engine_bridge.py &
BRIDGE_PID=$!

echo "=================================================="
echo " [SUCCESS] Dual-Engine System is LIVE and ONLINE!"
echo " - Nova Titan PID : $TITAN_PID (Port 8080)"
echo " - Nova Spark PID : $SPARK_PID (Port 8081)"
echo " - Bridge PID     : $BRIDGE_PID"
echo " Press CTRL + C to stop all engines safely."
echo "=================================================="

# স্ক্রিপ্ট বন্ধ করলে ক্লিন-আপ করার ব্যবস্থা
trap "echo '[!] Stopping Engines...'; kill $TITAN_PID $SPARK_PID $BRIDGE_PID; termux-wake-unlock; exit 0" SIGINT SIGTERM

wait
