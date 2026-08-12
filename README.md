# 🚀 Termux Dual-Server Suite (Python Flask)

A multi-threaded server application designed for **Termux on Android** (as well as Linux, macOS, and Windows). Running a single entrypoint launches **two separate, independent web servers** on different ports:

1. **Port 8000 (Storage Drive & File Server)**: Open storage dashboard, drag-and-drop uploader, disk metrics gauge, and HTML5 video streaming player.
2. **Port 6969 (Nexus Gate)**: A **passcode-protected** data relay portal (`password = hiddenrarety`) designed with a discrete UI to process asset URLs.

---

## ✨ Features Breakdown

### 🌐 Server 1: Port 8000 (`http://localhost:8000`)
- **File Management & Uploads**: Drag & drop multi-file uploader with real-time percentage progress bars.
- **Storage Metrics Gauge**: Live disk space monitoring (`shutil.disk_usage`).
- **Media Player & Byte-Range Video Streaming**: Stream HD videos and seek smoothly.

### 🔐 Server 2: Port 6969 (`http://localhost:6969`)
- **Passcode Protection**: Guarded by passcode `hiddenrarety`.
- **Discrete Nexus Gate**: Neutral tech UI with zero references to brand names or downloading terms.
- **Asset URL Processor**: Resolves resource links into direct streamable/downloadable payload URLs.

---

## 📱 Termux Quick Setup Guide

```bash
# 1. Update Termux and install Python
pkg update && pkg upgrade -y
pkg install python -y

# 2. Grant storage access (optional but recommended)
termux-setup-storage

# 3. Install requirements
pip install -r requirements.txt

# 4. Start both servers concurrently
python app.py
```

### Access Ports:
- **Server 1 (Storage Drive)**: `http://localhost:8000` (or `http://<PHONE_IP>:8000`)
- **Server 2 (Nexus Gate)**: `http://localhost:6969` (Passcode: `hiddenrarety`)
