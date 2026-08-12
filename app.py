import os
import re
import math
import shutil
import mimetypes
import threading
import multiprocessing
from datetime import datetime
from typing import List, Optional

import requests
from werkzeug.utils import secure_filename

# ==============================================================================
# MEDIA MIME TYPES & METADATA REGISTRY
# ==============================================================================
MEDIA_MIME_TYPES = {
    'mp4': 'video/mp4',
    'mkv': 'video/x-matroska',
    'webm': 'video/webm',
    'mov': 'video/quicktime',
    'avi': 'video/x-msvideo',
    'm4v': 'video/x-m4v',
    'ts': 'video/mp2t',
    'flv': 'video/x-flv',
    'mp3': 'audio/mpeg',
    'm4a': 'audio/mp4',
    'aac': 'audio/aac',
    'wav': 'audio/wav',
    'ogg': 'audio/ogg',
    'flac': 'audio/flac',
    'opus': 'audio/opus'
}

def format_bytes(size: int) -> str:
    if size == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

def check_ffmpeg_installed() -> bool:
    return shutil.which('ffmpeg') is not None

def get_media_mimetype(filepath: str) -> str:
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''
    if ext in MEDIA_MIME_TYPES:
        return MEDIA_MIME_TYPES[ext]
    guessed, _ = mimetypes.guess_type(filepath)
    return guessed or 'application/octet-stream'

def get_file_category(mime_type: str, filename: str) -> str:
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if (mime_type and mime_type.startswith('video/')) or ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'flv', 'm4v', 'ts']:
        return 'video'
    if (mime_type and mime_type.startswith('audio/')) or ext in ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'opus']:
        return 'audio'
    if (mime_type and mime_type.startswith('image/')) or ext in ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp']:
        return 'image'
    if ext in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'csv', 'md', 'xlsx', 'pptx', 'json', 'py', 'sh', 'html', 'css', 'js']:
        return 'document'
    if ext in ['zip', 'tar', 'gz', '7z', 'rar', 'bz2', 'xz']:
        return 'archive'
    return 'other'

def get_dir_size(path: str) -> int:
    total = 0
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
    return total

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
TRASH_FOLDER = os.path.join(UPLOAD_FOLDER, '.trash')
CHUNKS_FOLDER = os.path.join(UPLOAD_FOLDER, '.chunks')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRASH_FOLDER, exist_ok=True)
os.makedirs(CHUNKS_FOLDER, exist_ok=True)

def get_cache_info():
    trash_bytes = get_dir_size(TRASH_FOLDER)
    chunks_bytes = get_dir_size(CHUNKS_FOLDER)
    total_cache = trash_bytes + chunks_bytes
    return {
        'trash_bytes': trash_bytes,
        'chunks_bytes': chunks_bytes,
        'total_bytes': total_cache,
        'total_formatted': format_bytes(total_cache)
    }

def get_storage_info():
    total, used, free = shutil.disk_usage(UPLOAD_FOLDER)
    percent_used = round((used / total) * 100, 1)
    cache = get_cache_info()
    return {
        'total': total,
        'used': used,
        'free': free,
        'percent_used': percent_used,
        'total_formatted': format_bytes(total),
        'used_formatted': format_bytes(used),
        'free_formatted': format_bytes(free),
        'cache': cache
    }

GATE_PASSCODE = 'hiddenrarety'
AUTH_COOKIE_NAME = 'gate_auth_session'
AUTH_TOKEN_VALUE = 'nexus_authorized_6969'

# Check if FastAPI + Uvicorn is installed, otherwise fallback to Flask
try:
    from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
    USE_FASTAPI = True
except ImportError:
    from flask import Flask, render_template, request, jsonify, send_from_directory, Response, abort, session
    from werkzeug.serving import run_simple
    USE_FASTAPI = False


# ==============================================================================
# FASTAPI MODE
# ==============================================================================
if USE_FASTAPI:
    app_main = FastAPI(title="Termux Storage Drive", version="2.0.0")
    templates_main = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    app_main.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

    @app_main.get("/", response_class=HTMLResponse)
    async def main_index(request: Request):
        return templates_main.TemplateResponse("index.html", {"request": request})

    @app_main.get("/api/storage")
    async def api_storage():
        return {"success": True, "storage": get_storage_info()}

    @app_main.get("/api/cache/info")
    async def api_cache_info():
        return {"success": True, "cache": get_cache_info()}

    @app_main.post("/api/cache/purge")
    async def api_cache_purge():
        cache_before = get_cache_info()['total_bytes']
        if os.path.exists(TRASH_FOLDER):
            shutil.rmtree(TRASH_FOLDER, ignore_errors=True)
            os.makedirs(TRASH_FOLDER, exist_ok=True)
        if os.path.exists(CHUNKS_FOLDER):
            shutil.rmtree(CHUNKS_FOLDER, ignore_errors=True)
            os.makedirs(CHUNKS_FOLDER, exist_ok=True)
            
        reclaimed_bytes = cache_before
        return {
            'success': True,
            'message': f'Successfully reclaimed {format_bytes(reclaimed_bytes)} storage',
            'reclaimed_bytes': reclaimed_bytes,
            'reclaimed_formatted': format_bytes(reclaimed_bytes),
            'storage': get_storage_info(),
            'cache': get_cache_info()
        }

    @app_main.get("/api/files")
    async def list_files():
        files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath) and not filename.startswith('.'):
                stat = os.stat(filepath)
                mime_type = get_media_mimetype(filepath)
                category = get_file_category(mime_type, filename)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'formatted_size': format_bytes(stat.st_size),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'category': category,
                    'mime_type': mime_type,
                    'stream_url': f'/files/{filename}',
                    'download_url': f'/download/{filename}'
                })
        files.sort(key=lambda x: x['modified'], reverse=True)
        return {'success': True, 'files': files, 'count': len(files)}

    @app_main.post("/api/upload")
    async def upload_file(files: List[UploadFile] = File(...)):
        saved_files = []
        for file in files:
            if file and file.filename:
                raw_filename = secure_filename(file.filename) or f"file_{int(datetime.now().timestamp())}"
                destination = os.path.join(UPLOAD_FOLDER, raw_filename)
                if os.path.exists(destination):
                    base, ext = os.path.splitext(raw_filename)
                    raw_filename = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                    destination = os.path.join(UPLOAD_FOLDER, raw_filename)
                with open(destination, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_files.append(raw_filename)
        return {'success': True, 'message': f'Successfully uploaded {len(saved_files)} file(s)', 'saved_files': saved_files}

    @app_main.post("/api/upload/chunk")
    async def upload_chunk(
        chunk: UploadFile = File(...),
        upload_id: str = Form(...),
        filename: str = Form(...),
        chunk_index: int = Form(...),
        total_chunks: int = Form(...)
    ):
        safe_upload_id = secure_filename(upload_id)
        safe_filename = secure_filename(filename)
        chunk_dir = os.path.join(CHUNKS_FOLDER, safe_upload_id)
        os.makedirs(chunk_dir, exist_ok=True)
        chunk_filepath = os.path.join(chunk_dir, f"chunk_{chunk_index:05d}")
        
        with open(chunk_filepath, "wb") as buffer:
            shutil.copyfileobj(chunk.file, buffer)

        received_chunks = len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
        if received_chunks == total_chunks:
            destination = os.path.join(UPLOAD_FOLDER, safe_filename)
            if os.path.exists(destination):
                base, ext = os.path.splitext(safe_filename)
                safe_filename = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                destination = os.path.join(UPLOAD_FOLDER, safe_filename)

            with open(destination, 'wb') as final_file:
                for i in range(total_chunks):
                    c_path = os.path.join(chunk_dir, f"chunk_{i:05d}")
                    if os.path.exists(c_path):
                        with open(c_path, 'rb') as c_file:
                            shutil.copyfileobj(c_file, final_file)

            shutil.rmtree(chunk_dir, ignore_errors=True)
            return {'success': True, 'completed': True, 'message': 'File uploaded successfully', 'filename': safe_filename}

        return {'success': True, 'completed': False, 'received_chunks': received_chunks, 'total_chunks': total_chunks}

    @app_main.delete("/api/files/{filename}")
    async def delete_file(filename: str):
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")

        trash_destination = os.path.join(TRASH_FOLDER, safe_name)
        if os.path.exists(trash_destination):
            base, ext = os.path.splitext(safe_name)
            trash_destination = os.path.join(TRASH_FOLDER, f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")

        shutil.move(filepath, trash_destination)
        return {'success': True, 'message': f'File {safe_name} moved to trash'}

    @app_main.get("/files/{filename}")
    async def serve_file(filename: str, request: Request):
        """High-performance async Byte-Range media streaming with Safari bytes=0-1 probe support."""
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.isfile(filepath):
            raise HTTPException(status_code=404, detail="File not found")

        file_size = os.path.getsize(filepath)
        mimetype = get_media_mimetype(filepath)
        range_header = request.headers.get("range")

        if range_header:
            byte1, byte2 = 0, None
            match = re.search(r'bytes=(\d+)-(\d+)?', range_header)
            if match:
                g = match.groups()
                byte1 = int(g[0])
                if g[1]:
                    byte2 = int(g[1])
            
            # Handle Safari probe (bytes=0-1)
            if byte1 == 0 and byte2 == 1:
                byte2 = 1 

            chunk_size = 1024 * 1024 * 2
            if byte2 is None:
                byte2 = min(byte1 + chunk_size - 1, file_size - 1)
            length = byte2 - byte1 + 1

            def iterfile():
                with open(filepath, 'rb') as f:
                    f.seek(byte1)
                    remaining = length
                    while remaining > 0:
                        read_bytes = min(1024 * 64, remaining)
                        data = f.read(read_bytes)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(length),
                'Cache-Control': 'public, max-age=3600'
            }
            return StreamingResponse(iterfile(), status_code=206, media_type=mimetype, headers=headers)

        return FileResponse(filepath, media_type=mimetype, headers={'Accept-Ranges': 'bytes'})

    @app_main.get("/transcode/{filename}")
    async def transcode_file(filename: str):
        """On-the-fly FFmpeg AAC audio transcoder for Safari, Chrome & Brave compatibility."""
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.isfile(filepath):
            raise HTTPException(status_code=404, detail="File not found")

        if not check_ffmpeg_installed():
            raise HTTPException(status_code=500, detail="FFmpeg is not installed on server. Run 'pkg install ffmpeg' in Termux.")

        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-i', filepath,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', 'frag_keyframe+empty_moov',
            '-f', 'mp4',
            'pipe:1'
        ]

        import subprocess
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def iter_transcode():
            try:
                while True:
                    data = proc.stdout.read(64 * 1024)
                    if not data:
                        break
                    yield data
            finally:
                proc.terminate()

        headers = {'Accept-Ranges': 'bytes', 'Cache-Control': 'no-cache'}
        return StreamingResponse(iter_transcode(), media_type="video/mp4", headers=headers)


    @app_main.get("/download/{filename}")
    async def download_file(filename: str):
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.isfile(filepath):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(filepath, filename=safe_name)

    # Relay Server 2
    app_relay = FastAPI(title="Nexus Gate Relay", version="2.0.0")
    templates_relay = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    app_relay.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

    @app_relay.get("/", response_class=HTMLResponse)
    async def relay_index(request: Request):
        auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
        is_authenticated = (auth_cookie == AUTH_TOKEN_VALUE)
        return templates_relay.TemplateResponse("relay.html", {"request": request, "authenticated": is_authenticated})

    @app_relay.post("/api/auth")
    async def relay_auth(request: Request):
        data = await request.json() or {}
        if data.get('passcode') == GATE_PASSCODE:
            response = JSONResponse(content={'success': True, 'message': 'Access Granted'})
            response.set_cookie(key=AUTH_COOKIE_NAME, value=AUTH_TOKEN_VALUE, httponly=True, max_age=86400 * 7)
            return response
        return JSONResponse(content={'success': False, 'error': 'Invalid Passcode'}, status_code=401)

    @app_relay.post("/api/logout")
    async def relay_logout():
        response = JSONResponse(content={'success': True})
        response.delete_cookie(key=AUTH_COOKIE_NAME)
        return response

    @app_relay.post("/api/resolve")
    async def relay_resolve(request: Request):
        if request.cookies.get(AUTH_COOKIE_NAME) != AUTH_TOKEN_VALUE:
            return JSONResponse(content={'success': False, 'error': 'Unauthorized'}, status_code=401)
        data = await request.json() or {}
        target_url = data.get('url', '').strip()
        if not target_url:
            return JSONResponse(content={'success': False, 'error': 'URL required'}, status_code=400)
        try:
            ext = target_url.rsplit('.', 1)[-1].lower().split('?')[0] if '.' in target_url else ''
            if ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'mp3', 'wav', 'png', 'jpg', 'jpeg', 'zip', 'pdf']:
                filename = target_url.split('/')[-1].split('?')[0] or 'media_asset'
                return {'success': True, 'download_url': target_url, 'filename': filename, 'formatted_size': 'Direct Link', 'category': get_file_category('', filename)}

            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(target_url, headers=headers, timeout=12, allow_redirects=True)
            final_url = resp.url
            filename = final_url.split('/')[-1].split('?')[0] or 'extracted_payload'
            mime = resp.headers.get('Content-Type', '')
            return {'success': True, 'download_url': final_url, 'filename': filename, 'formatted_size': format_bytes(int(resp.headers.get('Content-Length', 0))), 'category': get_file_category(mime, filename)}
        except Exception as e:
            return JSONResponse(content={'success': False, 'error': str(e)}, status_code=500)


# ==============================================================================
# FLASK FALLBACK MODE (FOR TERMUX WITHOUT RUST COMPILER)
# ==============================================================================
else:
    app_main_flask = Flask(__name__, template_folder='templates', static_folder='static')
    app_main_flask.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    @app_main_flask.route('/')
    def flask_main_index():
        return render_template('index.html')

    @app_main_flask.route('/api/storage')
    def flask_api_storage():
        return jsonify({'success': True, 'storage': get_storage_info()})

    @app_main_flask.route('/api/cache/info')
    def flask_api_cache_info():
        return jsonify({'success': True, 'cache': get_cache_info()})

    @app_main_flask.route('/api/cache/purge', methods=['POST'])
    def flask_api_cache_purge():
        cache_before = get_cache_info()['total_bytes']
        shutil.rmtree(TRASH_FOLDER, ignore_errors=True); os.makedirs(TRASH_FOLDER, exist_ok=True)
        shutil.rmtree(CHUNKS_FOLDER, ignore_errors=True); os.makedirs(CHUNKS_FOLDER, exist_ok=True)
        return jsonify({'success': True, 'message': f'Reclaimed {format_bytes(cache_before)}', 'storage': get_storage_info(), 'cache': get_cache_info()})

    @app_main_flask.route('/api/files')
    def flask_list_files():
        files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath) and not filename.startswith('.'):
                stat = os.stat(filepath)
                mime = get_media_mimetype(filepath)
                files.append({'name': filename, 'size': stat.st_size, 'formatted_size': format_bytes(stat.st_size), 'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'), 'category': get_file_category(mime, filename), 'mime_type': mime, 'stream_url': f'/files/{filename}', 'download_url': f'/download/{filename}'})
        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'success': True, 'files': files, 'count': len(files)})

    @app_main_flask.route('/api/upload', methods=['POST'])
    def flask_upload():
        uploaded_files = request.files.getlist('files') or request.files.getlist('file')
        saved_files = []
        for file in uploaded_files:
            if file and file.filename:
                raw_filename = secure_filename(file.filename) or 'file'
                dest = os.path.join(UPLOAD_FOLDER, raw_filename)
                file.save(dest)
                saved_files.append(raw_filename)
        return jsonify({'success': True, 'saved_files': saved_files})

    @app_main_flask.route('/api/upload/chunk', methods=['POST'])
    def flask_upload_chunk():
        file_chunk = request.files.get('chunk')
        upload_id = secure_filename(request.form.get('upload_id', ''))
        filename = secure_filename(request.form.get('filename', ''))
        chunk_index = int(request.form.get('chunk_index', 0))
        total_chunks = int(request.form.get('total_chunks', 1))

        chunk_dir = os.path.join(CHUNKS_FOLDER, upload_id)
        os.makedirs(chunk_dir, exist_ok=True)
        file_chunk.save(os.path.join(chunk_dir, f"chunk_{chunk_index:05d}"))

        if len(os.listdir(chunk_dir)) == total_chunks:
            dest = os.path.join(UPLOAD_FOLDER, filename)
            with open(dest, 'wb') as final_file:
                for i in range(total_chunks):
                    c_path = os.path.join(chunk_dir, f"chunk_{i:05d}")
                    if os.path.exists(c_path):
                        with open(c_path, 'rb') as c_file: shutil.copyfileobj(c_file, final_file)
            shutil.rmtree(chunk_dir, ignore_errors=True)
            return jsonify({'success': True, 'completed': True, 'filename': filename})
        return jsonify({'success': True, 'completed': False})

    @app_main_flask.route('/api/files/<path:filename>', methods=['DELETE'])
    def flask_delete_file(filename):
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if os.path.exists(filepath):
            shutil.move(filepath, os.path.join(TRASH_FOLDER, safe_name))
        return jsonify({'success': True})

    @app_main_flask.route('/files/<path:filename>')
    def flask_serve_file(filename):
        safe_name = secure_filename(filename)
        return send_from_directory(UPLOAD_FOLDER, safe_name, conditional=True, mimetype=get_media_mimetype(os.path.join(UPLOAD_FOLDER, safe_name)))

    @app_main_flask.route('/transcode/<path:filename>')
    def flask_transcode_file(filename):
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.isfile(filepath):
            abort(404)

        if not check_ffmpeg_installed():
            return jsonify({'success': False, 'error': "FFmpeg is not installed on server. Run 'pkg install ffmpeg' in Termux."}), 500

        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-i', filepath,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', 'frag_keyframe+empty_moov',
            '-f', 'mp4',
            'pipe:1'
        ]

        import subprocess
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def iter_stream():
            try:
                while True:
                    data = proc.stdout.read(64 * 1024)
                    if not data:
                        break
                    yield data
            finally:
                proc.terminate()

        return Response(iter_stream(), mimetype="video/mp4", headers={'Accept-Ranges': 'bytes'})


    @app_main_flask.route('/download/<path:filename>')
    def flask_download_file(filename):
        return send_from_directory(UPLOAD_FOLDER, secure_filename(filename), as_attachment=True)

    app_relay_flask = Flask(__name__, template_folder='templates', static_folder='static')
    app_relay_flask.secret_key = 'nexus-secret-6969'

    @app_relay_flask.route('/')
    def flask_relay_index():
        return render_template('relay.html', authenticated=session.get('auth', False))

    @app_relay_flask.route('/api/auth', methods=['POST'])
    def flask_relay_auth():
        if request.json.get('passcode') == GATE_PASSCODE:
            session['auth'] = True
            return jsonify({'success': True, 'message': 'Access Granted'})
        return jsonify({'success': False, 'error': 'Invalid Passcode'}), 401

    @app_relay_flask.route('/api/logout', methods=['POST'])
    def flask_relay_logout():
        session.pop('auth', None)
        return jsonify({'success': True})

    @app_relay_flask.route('/api/resolve', methods=['POST'])
    def flask_relay_resolve():
        if not session.get('auth'): return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        target_url = request.json.get('url', '').strip()
        resp = requests.get(target_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        filename = resp.url.split('/')[-1].split('?')[0] or 'asset'
        return jsonify({'success': True, 'download_url': resp.url, 'filename': filename, 'formatted_size': 'Direct Link', 'category': get_file_category(resp.headers.get('Content-Type', ''), filename)})


# ==============================================================================
# DUAL SERVER LAUNCHER
# ==============================================================================
def run_main():
    if USE_FASTAPI:
        print("🚀 Port 8000: Storage Drive active on http://0.0.0.0:8000 (FastAPI Async ASGI)")
        uvicorn.run(app_main, host="0.0.0.0", port=8000, log_level="warning")
    else:
        print("🚀 Port 8000: Storage Drive active on http://0.0.0.0:8000 (Flask Lightweight WSGI)")
        run_simple('0.0.0.0', 8000, app_main_flask, threaded=True)

def run_relay():
    if USE_FASTAPI:
        print("🔐 Port 6969: Nexus Gate active on http://0.0.0.0:6969 (FastAPI Async ASGI)")
        uvicorn.run(app_relay, host="0.0.0.0", port=6969, log_level="warning")
    else:
        print("🔐 Port 6969: Nexus Gate active on http://0.0.0.0:6969 (Flask Lightweight WSGI)")
        run_simple('0.0.0.0', 6969, app_relay_flask, threaded=True)

if __name__ == "__main__":
    if not USE_FASTAPI:
        print("⚡ [Termux Notice] Running in Lightweight Flask Mode (Zero Rust compilation required).")
    else:
        print("⚡ [High-Performance Mode] Running in FastAPI + Uvicorn Async Mode.")

    p1 = multiprocessing.Process(target=run_main)
    p2 = multiprocessing.Process(target=run_relay)

    p1.start()
    p2.start()

    print("==================================================================")
    print("  🌐 SERVER 1: http://localhost:8000 (Storage Drive)")
    print("  🔐 SERVER 2: http://localhost:6969 (Nexus Gate | Passcode: hiddenrarety)")
    print("==================================================================")

    p1.join()
    p2.join()
