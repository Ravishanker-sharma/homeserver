import os
import re
import math
import shutil
import mimetypes
import threading
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, abort, session
from werkzeug.utils import secure_filename

# ==============================================================================
# SERVER 1: PRIMARY FILE STORAGE DRIVE (PORT 8000)
# ==============================================================================
app_main = Flask(__name__, template_folder='templates', static_folder='static')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
TRASH_FOLDER = os.path.join(UPLOAD_FOLDER, '.trash')
CHUNKS_FOLDER = os.path.join(UPLOAD_FOLDER, '.chunks')

app_main.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app_main.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRASH_FOLDER, exist_ok=True)
os.makedirs(CHUNKS_FOLDER, exist_ok=True)

def format_bytes(size):
    if size == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

def get_dir_size(path):
    total = 0
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
    return total

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

def get_media_mimetype(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''
    if ext in MEDIA_MIME_TYPES:
        return MEDIA_MIME_TYPES[ext]
    guessed, _ = mimetypes.guess_type(filepath)
    return guessed or 'application/octet-stream'

def get_file_category(mime_type, filename):
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

def get_storage_info():
    path = app_main.config['UPLOAD_FOLDER']
    total, used, free = shutil.disk_usage(path)
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

@app_main.route('/')
def main_index():
    return render_template('index.html')

@app_main.route('/api/storage', methods=['GET'])
def api_storage():
    try:
        return jsonify({'success': True, 'storage': get_storage_info()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/api/cache/info', methods=['GET'])
def api_cache_info():
    try:
        return jsonify({'success': True, 'cache': get_cache_info()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/api/cache/purge', methods=['POST'])
def api_cache_purge():
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
        
        return jsonify({
            'success': True,
            'message': f'Successfully reclaimed {reclaimed_formatted} storage',
            'reclaimed_bytes': reclaimed_bytes,
            'reclaimed_formatted': reclaimed_formatted,
            'storage': get_storage_info(),
            'cache': get_cache_info()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/api/files', methods=['GET'])
def list_files():
    try:
        files = []
        folder = app_main.config['UPLOAD_FOLDER']
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
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
        return jsonify({'success': True, 'files': files, 'count': len(files)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part in request'}), 400
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or (len(uploaded_files) == 1 and uploaded_files[0].filename == ''):
            uploaded_files = request.files.getlist('file')
        if not uploaded_files or uploaded_files[0].filename == '':
            return jsonify({'success': False, 'error': 'No file selected for upload'}), 400
            
        saved_files = []
        for file in uploaded_files:
            if file and file.filename:
                raw_filename = secure_filename(file.filename) or f"file_{int(datetime.now().timestamp())}"
                destination = os.path.join(app_main.config['UPLOAD_FOLDER'], raw_filename)
                if os.path.exists(destination):
                    base, ext = os.path.splitext(raw_filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    raw_filename = f"{base}_{timestamp}{ext}"
                    destination = os.path.join(app_main.config['UPLOAD_FOLDER'], raw_filename)
                file.save(destination)
                saved_files.append(raw_filename)
                
        return jsonify({'success': True, 'message': f'Successfully uploaded {len(saved_files)} file(s)', 'saved_files': saved_files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/api/upload/chunk', methods=['POST'])
def upload_chunk():
    try:
        file_chunk = request.files.get('chunk')
        upload_id = secure_filename(request.form.get('upload_id', ''))
        filename = secure_filename(request.form.get('filename', ''))
        chunk_index = int(request.form.get('chunk_index', 0))
        total_chunks = int(request.form.get('total_chunks', 1))

        if not file_chunk or not upload_id or not filename:
            return jsonify({'success': False, 'error': 'Missing chunk parameters'}), 400

        chunk_dir = os.path.join(app_main.config['UPLOAD_FOLDER'], '.chunks', upload_id)
        os.makedirs(chunk_dir, exist_ok=True)

        chunk_filepath = os.path.join(chunk_dir, f"chunk_{chunk_index:05d}")
        file_chunk.save(chunk_filepath)

        received_chunks = len([f for f in os.listdir(chunk_dir) if f.startswith('chunk_')])
        if received_chunks == total_chunks:
            destination = os.path.join(app_main.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(destination):
                base, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{base}_{timestamp}{ext}"
                destination = os.path.join(app_main.config['UPLOAD_FOLDER'], filename)

            with open(destination, 'wb') as final_file:
                for i in range(total_chunks):
                    c_path = os.path.join(chunk_dir, f"chunk_{i:05d}")
                    if os.path.exists(c_path):
                        with open(c_path, 'rb') as c_file:
                            shutil.copyfileobj(c_file, final_file)

            shutil.rmtree(chunk_dir, ignore_errors=True)

            return jsonify({
                'success': True,
                'completed': True,
                'message': 'File uploaded and assembled successfully',
                'filename': filename
            })

        return jsonify({
            'success': True,
            'completed': False,
            'received_chunks': received_chunks,
            'total_chunks': total_chunks
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/api/files/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        safe_name = secure_filename(filename)
        filepath = os.path.join(app_main.config['UPLOAD_FOLDER'], safe_name)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
        trash_destination = os.path.join(TRASH_FOLDER, safe_name)
        if os.path.exists(trash_destination):
            base, ext = os.path.splitext(safe_name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            trash_destination = os.path.join(TRASH_FOLDER, f"{base}_{timestamp}{ext}")
            
        shutil.move(filepath, trash_destination)
        return jsonify({'success': True, 'message': f'File {safe_name} moved to trash'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/files/<path:filename>')
def serve_file(filename):
    """Serves media files with Werkzeug native conditional Byte-Range support for smooth streaming & audio."""
    safe_name = secure_filename(filename)
    filepath = os.path.join(app_main.config['UPLOAD_FOLDER'], safe_name)
    if not os.path.isfile(filepath):
        abort(404)

    mimetype = get_media_mimetype(filepath)

    response = send_from_directory(
        app_main.config['UPLOAD_FOLDER'],
        safe_name,
        conditional=True,
        mimetype=mimetype
    )
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


@app_main.route('/download/<path:filename>')
def download_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(app_main.config['UPLOAD_FOLDER'], safe_name, as_attachment=True)


# ==============================================================================
# SERVER 2: DISCRETE RELAY NODE & ASSET GATEWAY (PORT 6969)
# ==============================================================================
app_relay = Flask(__name__, template_folder='templates', static_folder='static')
app_relay.secret_key = 'nexus-gate-secret-key-6969'
GATE_PASSCODE = 'hiddenrarety'

@app_relay.route('/')
def relay_index():
    is_auth = session.get('authenticated', False)
    return render_template('relay.html', authenticated=is_auth)

@app_relay.route('/api/auth', methods=['POST'])
def relay_auth():
    data = request.get_json() or {}
    passcode = data.get('passcode', '')
    if passcode == GATE_PASSCODE:
        session['authenticated'] = True
        return jsonify({'success': True, 'message': 'Access Granted'})
    return jsonify({'success': False, 'error': 'Invalid Passcode'}), 401

@app_relay.route('/api/logout', methods=['POST'])
def relay_logout():
    session.pop('authenticated', None)
    return jsonify({'success': True})

@app_relay.route('/api/resolve', methods=['POST'])
def relay_resolve():
    if not session.get('authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized. Passcode required.'}), 401
        
    data = request.get_json() or {}
    target_url = data.get('url', '').strip()
    if not target_url:
        return jsonify({'success': False, 'error': 'URL target required'}), 400

    try:
        # Check if URL is already a direct downloadable/streamable media asset
        ext = target_url.rsplit('.', 1)[-1].lower().split('?')[0] if '.' in target_url else ''
        if ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'mp3', 'wav', 'png', 'jpg', 'jpeg', 'zip', 'pdf']:
            filename = target_url.split('/')[-1].split('?')[0] or 'media_asset'
            category = get_file_category('', filename)
            return jsonify({
                'success': True,
                'download_url': target_url,
                'filename': filename,
                'formatted_size': 'Direct Link',
                'category': category
            })

        # Process shared resource URL link discreetly via backend resolver
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Optional custom account cookie if provided in environment
        ndus_cookie = os.environ.get('RELAY_TOKEN', '')
        cookies = {'ndus': ndus_cookie} if ndus_cookie else {}

        resp = requests.get(target_url, headers=headers, cookies=cookies, timeout=12, allow_redirects=True)
        final_url = resp.url
        
        # If redirected to direct stream link
        filename = final_url.split('/')[-1].split('?')[0] or 'extracted_payload'
        mime = resp.headers.get('Content-Type', '')
        category = get_file_category(mime, filename)
        
        return jsonify({
            'success': True,
            'download_url': final_url,
            'filename': filename,
            'formatted_size': format_bytes(int(resp.headers.get('Content-Length', 0))),
            'category': category
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to process link: {str(e)}'}), 500


# ==============================================================================
# UNIFIED DUAL-THREAD LAUNCHER
# ==============================================================================
from werkzeug.serving import run_simple

def run_main():
    print("🚀 Port 8000: Storage Drive active on http://0.0.0.0:8000")
    run_simple('0.0.0.0', 8000, app_main, threaded=True)

def run_relay():
    print("🔐 Port 6969: Nexus Gate active on http://0.0.0.0:6969 (Passcode Required)")
    run_simple('0.0.0.0', 6969, app_relay, threaded=True)

if __name__ == '__main__':
    t1 = threading.Thread(target=run_main, daemon=True)
    t2 = threading.Thread(target=run_relay, daemon=True)
    
    t1.start()
    t2.start()
    
    print("==================================================================")
    print("  🌐 SERVER 1: http://localhost:8000 (File Manager & Storage Drive)")
    print("  🔐 SERVER 2: http://localhost:6969 (Nexus Gate | Passcode: hiddenrarety)")
    print("==================================================================")
    
    t1.join()
    t2.join()


