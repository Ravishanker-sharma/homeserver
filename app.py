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
app_main.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app_main.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def format_bytes(size):
    if size == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

def get_file_category(mime_type, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if (mime_type and mime_type.startswith('video/')) or ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'flv', 'm4v']:
        return 'video'
    if (mime_type and mime_type.startswith('audio/')) or ext in ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac']:
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
    return {
        'total': total,
        'used': used,
        'free': free,
        'percent_used': percent_used,
        'total_formatted': format_bytes(total),
        'used_formatted': format_bytes(used),
        'free_formatted': format_bytes(free)
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

@app_main.route('/api/files', methods=['GET'])
def list_files():
    try:
        files = []
        folder = app_main.config['UPLOAD_FOLDER']
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath) and not filename.startswith('.'):
                stat = os.stat(filepath)
                mime_type, _ = mimetypes.guess_type(filepath)
                mime_type = mime_type or 'application/octet-stream'
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

@app_main.route('/api/files/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        safe_name = secure_filename(filename)
        filepath = os.path.join(app_main.config['UPLOAD_FOLDER'], safe_name)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'File {safe_name} deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app_main.route('/files/<path:filename>')
def serve_file(filename):
    safe_name = secure_filename(filename)
    filepath = os.path.join(app_main.config['UPLOAD_FOLDER'], safe_name)
    if not os.path.isfile(filepath):
        abort(404)
        
    file_size = os.path.getsize(filepath)
    range_header = request.headers.get('Range', None)
    
    if range_header:
        byte1, byte2 = 0, None
        match = re.search(r'bytes=(\d+)-(\d+)?', range_header)
        if match:
            groups = match.groups()
            byte1 = int(groups[0])
            if groups[1]:
                byte2 = int(groups[1])
                
        chunk_size = 1024 * 1024 * 2
        if byte2 is None:
            byte2 = min(byte1 + chunk_size - 1, file_size - 1)
            
        length = byte2 - byte1 + 1
        
        def generate():
            with open(filepath, 'rb') as f:
                f.seek(byte1)
                remaining = length
                while remaining > 0:
                    read_bytes = min(1024 * 64, remaining)
                    chunk = f.read(read_bytes)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
                    
        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or 'application/octet-stream'
        
        response = Response(generate(), 206, mimetype=mime_type, content_type=mime_type, direct_passthrough=True)
        response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(length))
        return response

    return send_from_directory(app_main.config['UPLOAD_FOLDER'], safe_name)

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


