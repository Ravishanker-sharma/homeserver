import os
import re
import math
import shutil
import mimetypes
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Allow up to 2GB upload size
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def format_bytes(size):
    """Formats bytes into human readable string (KB, MB, GB, etc.)"""
    if size == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

def get_file_category(mime_type, filename):
    """Categorizes file type for frontend filtering and icon display."""
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
    """Gets storage statistics for the drive hosting uploads."""
    path = app.config['UPLOAD_FOLDER']
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

@app.route('/')
def index():
    """Serves the main frontend dashboard."""
    return render_template('index.html')

@app.route('/api/storage', methods=['GET'])
def api_storage():
    """Returns disk space usage telemetry."""
    try:
        return jsonify({'success': True, 'storage': get_storage_info()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """Lists all files in the upload folder with metadata."""
    try:
        files = []
        folder = app.config['UPLOAD_FOLDER']
        
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
        
        # Sort files by newest modified first
        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'success': True, 'files': files, 'count': len(files)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handles file uploads with multipart form data."""
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
                raw_filename = secure_filename(file.filename)
                if not raw_filename:
                    # Fallback for filenames that secure_filename strips completely
                    raw_filename = f"file_{int(datetime.now().timestamp())}"
                
                # Avoid overwriting existing files by appending timestamp if duplicate
                destination = os.path.join(app.config['UPLOAD_FOLDER'], raw_filename)
                if os.path.exists(destination):
                    base, ext = os.path.splitext(raw_filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    raw_filename = f"{base}_{timestamp}{ext}"
                    destination = os.path.join(app.config['UPLOAD_FOLDER'], raw_filename)
                
                file.save(destination)
                saved_files.append(raw_filename)
                
        return jsonify({
            'success': True, 
            'message': f'Successfully uploaded {len(saved_files)} file(s)',
            'saved_files': saved_files
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Deletes a file from the server."""
    try:
        safe_name = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'File {safe_name} deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serves files with HTTP Byte-Range support for smooth video/audio streaming."""
    safe_name = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    
    if not os.path.isfile(filepath):
        abort(404)
        
    file_size = os.path.getsize(filepath)
    range_header = request.headers.get('Range', None)
    
    # Handle HTTP Range requests for video seeking/streaming
    if range_header:
        byte1, byte2 = 0, None
        match = re.search(r'bytes=(\d+)-(\d+)?', range_header)
        if match:
            groups = match.groups()
            byte1 = int(groups[0])
            if groups[1]:
                byte2 = int(groups[1])
                
        chunk_size = 1024 * 1024 * 2  # 2MB chunks for smooth streaming
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
        
        response = Response(
            generate(),
            206,
            mimetype=mime_type,
            content_type=mime_type,
            direct_passthrough=True
        )
        response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(length))
        return response

    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Triggers file download."""
    safe_name = secure_filename(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name, as_attachment=True)

if __name__ == '__main__':
    # Listen on all interfaces (0.0.0.0) so Termux server is accessible over Wi-Fi / Local Network
    port = int(os.environ.get('PORT', 5050))
    print(f"🚀 Termux Media Server starting on http://0.0.0.0:{port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except OSError:
        port = 8080
        print(f"⚠️ Port busy, starting on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)

