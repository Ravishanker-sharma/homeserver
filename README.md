# 🚀 Termux Dual-Server Suite (Python Hybrid Engine)

A lightweight, high-performance dual-server web application designed for **Termux on Android** (as well as Linux, macOS, and Windows). 

Running `python app.py` starts **two independent servers** simultaneously:

1. **Server 1 (Port 8000)**: `http://localhost:8000` (Storage Drive, Drag & Drop 5MB Chunked Uploader, Trash & Cache Purger, Byte-Range HD Video Streamer).
2. **Server 2 (Port 6969)**: `http://localhost:6969` (**Nexus Gate** | Passcode: `hiddenrarety` | Discrete URL asset processor).

---

## ⚡ Hybrid Engine Support (Flask + FastAPI Auto-Detection)

The application includes an **Automatic Engine Fallback System**:
- **Lightweight Mode (Default)**: Uses standard Python Flask (`pip install -r requirements.txt`). Requires **ZERO C/Rust compilers** on Termux! Instant 5-second setup.
- **Async High-Concurrency Mode**: Automatically activates if `fastapi` and `uvicorn` are installed (`pip install fastapi uvicorn`).

---

## 📱 Termux Quick Setup Guide (Android)

### Option A: Standard Setup (Instant - Zero Rust Compiler Required)
```bash
# 1. Update Termux and install Python & git
pkg update && pkg upgrade -y
pkg install python git -y

# 2. Grant storage permissions
termux-setup-storage

# 3. Install lightweight requirements (Instant, no compilation errors!)
pip install -r requirements.txt

# 4. Start the servers
python app.py
```

### Option B: Optional FastAPI Mode in Termux (Requires Rust)
If you want FastAPI + Uvicorn async mode on Termux:
```bash
pkg install rust clang -y
pip install fastapi uvicorn
python app.py
```

---

## 📁 Access Links
- **Server 1 (Storage Drive)**: `http://localhost:8000` (or `http://<PHONE_IP>:8000`)
- **Server 2 (Nexus Gate)**: `http://localhost:6969` (Passcode: `hiddenrarety`)
