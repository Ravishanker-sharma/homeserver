import os
import re
import math
import shutil
import mimetypes
import multiprocessing
from datetime import datetime
from typing import List, Optional

import requests
import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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


# ==============================================================================
# FASTAPI SERVER 1: PRIMARY FILE STORAGE DRIVE & STREAMER (PORT 8000)
# ==============================================================================
app_main = FastAPI(title="Termux Storage Drive", version="2.0.0")
templates_main = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app_main.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app_main.get("/", response_class=HTMLResponse)
async def main_index(request: Request):
    return templates_main.TemplateResponse("index.html", {"request": request})

@app_main.get("/api/storage")
async def api_storage():
    try:
        return {"success": True, "storage": get_storage_info()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.get("/api/cache/info")
async def api_cache_info():
    try:
        return {"success": True, "cache": get_cache_info()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.post("/api/cache/purge")
async def api_cache_purge():
    try:
        cache_before = get_cache_info()['total_bytes']
        if os.path.exists(TRASH_FOLDER):
            shutil.rmtree(TRASH_FOLDER, ignore_errors=True)
            os.makedirs(TRASH_FOLDER, exist_ok=True)
            
        if os.path.exists(CHUNKS_FOLDER):
            shutil.rmtree(CHUNKS_FOLDER, ignore_errors=True)
            os.makedirs(CHUNKS_FOLDER, exist_ok=True)
            
        reclaimed_bytes = cache_before
        reclaimed_formatted = format_bytes(reclaimed_bytes)
        
        return {
            'success': True,
            'message': f'Successfully reclaimed {reclaimed_formatted} storage',
            'reclaimed_bytes': reclaimed_bytes,
            'reclaimed_formatted': reclaimed_formatted,
            'storage': get_storage_info(),
            'cache': get_cache_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.get("/api/files")
async def list_files():
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.post("/api/upload")
async def upload_file(files: List[UploadFile] = File(...)):
    try:
        saved_files = []
        for file in files:
            if file and file.filename:
                raw_filename = secure_filename(file.filename) or f"file_{int(datetime.now().timestamp())}"
                destination = os.path.join(UPLOAD_FOLDER, raw_filename)
                if os.path.exists(destination):
                    base, ext = os.path.splitext(raw_filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    raw_filename = f"{base}_{timestamp}{ext}"
                    destination = os.path.join(UPLOAD_FOLDER, raw_filename)
                
                with open(destination, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_files.append(raw_filename)
                
        return {'success': True, 'message': f'Successfully uploaded {len(saved_files)} file(s)', 'saved_files': saved_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.post("/api/upload/chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    upload_id: str = Form(...),
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...)
):
    try:
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
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = f"{base}_{timestamp}{ext}"
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.delete("/api/files/{filename}")
async def delete_file(filename: str):
    try:
        safe_name = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")

        trash_destination = os.path.join(TRASH_FOLDER, safe_name)
        if os.path.exists(trash_destination):
            base, ext = os.path.splitext(safe_name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            trash_destination = os.path.join(TRASH_FOLDER, f"{base}_{timestamp}{ext}")

        shutil.move(filepath, trash_destination)
        return {'success': True, 'message': f'File {safe_name} moved to trash'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_main.get("/files/{filename}")
async def serve_file(filename: str, request: Request):
    """High-performance async Byte-Range media streaming endpoint."""
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

        chunk_size = 1024 * 1024 * 2  # 2MB chunks for smooth streaming
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

@app_main.get("/download/{filename}")
async def download_file(filename: str):
    safe_name = secure_filename(filename)
    filepath = os.path.join(UPLOAD_FOLDER, safe_name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=safe_name)


# ==============================================================================
# FASTAPI SERVER 2: DISCRETE RELAY NODE & GATEWAY (PORT 6969)
# ==============================================================================
app_relay = FastAPI(title="Nexus Gate Relay", version="2.0.0")
templates_relay = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app_relay.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

GATE_PASSCODE = 'hiddenrarety'
AUTH_COOKIE_NAME = 'gate_auth_session'
AUTH_TOKEN_VALUE = 'nexus_authorized_6969'

@app_relay.get("/", response_class=HTMLResponse)
async def relay_index(request: Request):
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    is_authenticated = (auth_cookie == AUTH_TOKEN_VALUE)
    return templates_relay.TemplateResponse("relay.html", {"request": request, "authenticated": is_authenticated})

@app_relay.post("/api/auth")
async def relay_auth(request: Request):
    data = await request.json() or {}
    passcode = data.get('passcode', '')
    if passcode == GATE_PASSCODE:
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
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if auth_cookie != AUTH_TOKEN_VALUE:
        return JSONResponse(content={'success': False, 'error': 'Unauthorized. Passcode required.'}, status_code=401)

    data = await request.json() or {}
    target_url = data.get('url', '').strip()
    if not target_url:
        return JSONResponse(content={'success': False, 'error': 'URL target required'}, status_code=400)

    try:
        ext = target_url.rsplit('.', 1)[-1].lower().split('?')[0] if '.' in target_url else ''
        if ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'mp3', 'wav', 'png', 'jpg', 'jpeg', 'zip', 'pdf']:
            filename = target_url.split('/')[-1].split('?')[0] or 'media_asset'
            category = get_file_category('', filename)
            return {
                'success': True,
                'download_url': target_url,
                'filename': filename,
                'formatted_size': 'Direct Link',
                'category': category
            }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        ndus_cookie = os.environ.get('RELAY_TOKEN', '')
        cookies = {'ndus': ndus_cookie} if ndus_cookie else {}

        resp = requests.get(target_url, headers=headers, cookies=cookies, timeout=12, allow_redirects=True)
        final_url = resp.url

        filename = final_url.split('/')[-1].split('?')[0] or 'extracted_payload'
        mime = resp.headers.get('Content-Type', '')
        category = get_file_category(mime, filename)

        return {
            'success': True,
            'download_url': final_url,
            'filename': filename,
            'formatted_size': format_bytes(int(resp.headers.get('Content-Length', 0))),
            'category': category
        }
    except Exception as e:
        return JSONResponse(content={'success': False, 'error': f'Failed to process link: {str(e)}'}, status_code=500)


# ==============================================================================
# DUAL UVICORN ASGI LAUNCHER
# ==============================================================================
def run_main():
    print("🚀 Port 8000: Storage Drive active on http://0.0.0.0:8000 (FastAPI ASGI)")
    uvicorn.run(app_main, host="0.0.0.0", port=8000, log_level="warning")

def run_relay():
    print("🔐 Port 6969: Nexus Gate active on http://0.0.0.0:6969 (FastAPI ASGI)")
    uvicorn.run(app_relay, host="0.0.0.0", port=6969, log_level="warning")

if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_main)
    p2 = multiprocessing.Process(target=run_relay)

    p1.start()
    p2.start()

    print("==================================================================")
    print("  🌐 SERVER 1: http://localhost:8000 (FastAPI Multi-Client Storage Drive)")
    print("  🔐 SERVER 2: http://localhost:6969 (FastAPI Nexus Gate | Passcode: hiddenrarety)")
    print("==================================================================")

    p1.join()
    p2.join()
