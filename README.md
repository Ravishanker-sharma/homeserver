# 🚀 Termux StreamDrive & Storage Vault (Python Flask)

A high-performance, visually stunning media server and file manager designed specifically for **Termux on Android** (as well as Linux, macOS, and Windows). 

It allows you to turn your phone or server into a private cloud drive where you can **upload files via drag-and-drop**, **stream HD videos smoothly** (with HTTP Range seeking), **preview music and photos**, and **monitor device storage space left in real-time**.

---

## ✨ Key Features

- 🎥 **Smooth Video Streaming**: Native HTTP 206 Partial Content / Byte-Range support allowing fast seeking/scrubbing forward & backward in videos.
- 💾 **Real-time Storage Telemetry**: Shows total, used, and free disk space left on your device (using standard Python libraries).
- 📤 **Drag & Drop Uploader**: Fast multi-file uploads with real-time percentage progress bars.
- 🖼️ **Built-in Media Players**: Video player modal, audio player preview, and photo lightbox viewer.
- 🔍 **Instant Search & Filtering**: Filter files by categories (Videos, Music, Images, Documents, Archives) or search by filename.
- 🎨 **Futuristic Cyber-Glassmorphism UI**: Beautiful dark mode interface with ambient glowing background effects and smooth micro-animations.
- 📱 **Termux Optimized**: Lightweight with ZERO heavy C-compiler binary dependencies. Works natively in Termux!

---

## 📱 Termux Quick Setup Guide (Android)

Follow these simple steps in your Termux app:

### Step 1: Update Termux and Install Python
```bash
pkg update && pkg upgrade -y
pkg install python -y
```

### Step 2: Grant Storage Access (Optional but Recommended)
To allow Termux to access phone storage:
```bash
termux-setup-storage
```

### Step 3: Clone / Copy Project & Install Dependencies
Navigate to your project directory and run:
```bash
pip install -r requirements.txt
```

### Step 4: Start the Server
```bash
python app.py
```

---

## 🌐 How to Access Your Server

Once started, the server outputs your local link:

1. **On the same phone (Termux device)**:
   Open Chrome / Firefox on your phone and go to:
   `http://localhost:5000`

2. **From other devices on the same Wi-Fi network (PC, Smart TV, Tablet)**:
   - Find your phone's IP address in Termux by running `ifconfig` or `ip addr show`.
   - Open browser on your PC/Tablet and go to:
     `http://<YOUR_PHONE_IP>:5000`
     *(Example: `http://192.168.1.15:5000`)*

---

## 📁 Project Structure

```
homeserver/
├── app.py              # Flask server backend (Byte-range video streaming + APIs)
├── requirements.txt    # Minimal dependencies (Flask & Werkzeug)
├── static/
│   ├── css/
│   │   └── style.css   # Dark glassmorphism design system & animations
│   └── js/
│       └── app.js      # Interactive uploader, file manager, & player modals
├── templates/
│   └── index.html      # Responsive HTML5 dashboard interface
└── uploads/            # Default storage folder for uploaded files
```
