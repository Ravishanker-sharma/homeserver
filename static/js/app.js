/**
 * Termux StreamDrive & Storage Vault Client JS
 * Featuring High-Speed Chunked Resumable Uploader & Speed/ETA Telemetry
 */

document.addEventListener('DOMContentLoaded', () => {
    let state = {
        files: [],
        currentCategory: 'all',
        searchQuery: '',
        storage: null
    };

    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB Chunks

    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const folderInput = document.getElementById('folder-input');
    const btnBrowse = document.getElementById('btn-browse');
    const btnBrowseFolder = document.getElementById('btn-browse-folder');
    
    const uploadQueue = document.getElementById('upload-queue');
    const queueList = document.getElementById('queue-list');
    const queueOverallStats = document.getElementById('queue-overall-stats');
    const btnClearQueue = document.getElementById('btn-clear-queue');
    
    const fileGrid = document.getElementById('file-grid');
    const emptyState = document.getElementById('empty-state');
    const searchInput = document.getElementById('search-input');
    const pillButtons = document.querySelectorAll('.pill-btn');
    
    // Storage elements
    const storageBar = document.getElementById('storage-bar');
    const storagePercent = document.getElementById('storage-percent');
    const statUsed = document.getElementById('stat-used');
    const statFree = document.getElementById('stat-free');
    const statCache = document.getElementById('stat-cache');
    const statTotal = document.getElementById('stat-total');
    const storageSub = document.getElementById('storage-status-sub');
    const btnCleanCache = document.getElementById('btn-clean-cache');

    
    // Modals
    const videoModal = document.getElementById('video-modal');
    const videoPlayer = document.getElementById('video-player');
    const videoTitle = document.getElementById('video-modal-title');
    const videoInfo = document.getElementById('video-modal-info');
    const videoDownload = document.getElementById('video-modal-download');
    const closeVideoBtn = document.getElementById('close-video-modal');
    
    const imageModal = document.getElementById('image-modal');
    const imagePreview = document.getElementById('image-preview');
    const imageTitle = document.getElementById('image-modal-title');
    const closeImageBtn = document.getElementById('close-image-modal');
    
    const audioModal = document.getElementById('audio-modal');
    const audioPlayer = document.getElementById('audio-player');
    const audioTitle = document.getElementById('audio-modal-title');
    const closeAudioBtn = document.getElementById('close-audio-modal');

    const categoryIcons = {
        video: '🎥', audio: '🎵', image: '🖼️', document: '📄', archive: '📦', other: '📎'
    };

    init();

    function init() {
        loadStorageInfo();
        loadFilesList();
        setupEventListeners();
        setInterval(loadStorageInfo, 30000);
    }

    async function loadStorageInfo() {
        try {
            const response = await fetch('/api/storage');
            const data = await response.json();
            if (data.success) {
                state.storage = data.storage;
                renderStorage(data.storage);
            }
        } catch (err) {
            console.error('Failed to load storage telemetry:', err);
        }
    }

    async function loadFilesList() {
        try {
            const response = await fetch('/api/files');
            const data = await response.json();
            if (data.success) {
                state.files = data.files;
                renderFiles();
            }
        } catch (err) {
            showToast('Error loading file list', 'error');
        }
    }

    function renderStorage(storage) {
        if (!storage) return;
        storageBar.style.width = `${storage.percent_used}%`;
        storagePercent.textContent = `${storage.percent_used}%`;
        statUsed.textContent = storage.used_formatted;
        statFree.textContent = storage.free_formatted;
        if (statCache && storage.cache) statCache.textContent = storage.cache.total_formatted;
        statTotal.textContent = storage.total_formatted;
        storageSub.textContent = `${storage.free_formatted} available space out of ${storage.total_formatted}`;
        
        if (storage.percent_used > 85) {
            storageBar.style.background = 'linear-gradient(90deg, #F59E0B, #F43F5E)';
        } else {
            storageBar.style.background = 'linear-gradient(90deg, var(--primary), var(--secondary))';
        }
    }


    function renderFiles() {
        const filtered = state.files.filter(file => {
            const matchesCategory = (state.currentCategory === 'all') || (file.category === state.currentCategory);
            const matchesSearch = file.name.toLowerCase().includes(state.searchQuery.toLowerCase());
            return matchesCategory && matchesSearch;
        });

        if (filtered.length === 0) {
            fileGrid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        fileGrid.style.display = 'grid';
        fileGrid.innerHTML = filtered.map(file => createFileCardHTML(file)).join('');
        attachFileCardListeners();
    }

    function createFileCardHTML(file) {
        const icon = categoryIcons[file.category] || categoryIcons.other;
        const encodedName = encodeURIComponent(file.name);
        
        let playBtnHTML = '';
        if (file.category === 'video') {
            playBtnHTML = `
                <button class="btn-action btn-stream" data-action="stream-video" data-file="${encodedName}">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    Stream
                </button>
            `;
        } else if (file.category === 'audio') {
            playBtnHTML = `
                <button class="btn-action btn-stream" data-action="stream-audio" data-file="${encodedName}">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    Play
                </button>
            `;
        } else if (file.category === 'image') {
            playBtnHTML = `
                <button class="btn-action" data-action="preview-image" data-file="${encodedName}">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    View
                </button>
            `;
        }

        return `
            <div class="file-card" data-filename="${file.name}">
                <div class="file-header">
                    <div class="file-icon-box category-${file.category}">
                        ${icon}
                    </div>
                    <div class="file-meta-primary">
                        <div class="file-name" title="${escapeHTML(file.name)}">${escapeHTML(file.name)}</div>
                        <div class="file-size-tag">${file.formatted_size}</div>
                    </div>
                </div>
                
                <div class="file-details">
                    <span>${file.category.toUpperCase()}</span>
                    <span>${file.modified.split(' ')[0]}</span>
                </div>
                
                <div class="file-actions">
                    ${playBtnHTML}
                    <a href="${file.download_url}" class="btn-action" title="Download File" download>
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Save
                    </a>
                    <button class="btn-action" data-action="copy-link" data-url="${window.location.origin}${file.stream_url}" title="Copy Link">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    </button>
                    <button class="btn-action btn-delete" data-action="delete" data-file="${encodedName}" title="Delete File">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            </div>
        `;
    }

    function attachFileCardListeners() {
        document.querySelectorAll('[data-action="stream-video"]').forEach(btn => {
            btn.addEventListener('click', () => openVideoModal(decodeURIComponent(btn.dataset.file)));
        });
        document.querySelectorAll('[data-action="stream-audio"]').forEach(btn => {
            btn.addEventListener('click', () => openAudioModal(decodeURIComponent(btn.dataset.file)));
        });
        document.querySelectorAll('[data-action="preview-image"]').forEach(btn => {
            btn.addEventListener('click', () => openImageModal(decodeURIComponent(btn.dataset.file)));
        });
        document.querySelectorAll('[data-action="copy-link"]').forEach(btn => {
            btn.addEventListener('click', () => {
                navigator.clipboard.writeText(btn.dataset.url);
                showToast('Stream link copied to clipboard!', 'success');
            });
        });
        document.querySelectorAll('[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const fileName = decodeURIComponent(btn.dataset.file);
                if (confirm(`Delete file "${fileName}"?`)) {
                    await deleteFile(fileName);
                }
            });
        });
    }

    // ==========================================
    // CHUNKED UPLOADER ENGINE
    // ==========================================
    function setupEventListeners() {
        btnBrowse.addEventListener('click', () => fileInput.click());
        btnBrowseFolder.addEventListener('click', () => folderInput.click());
        
        fileInput.addEventListener('change', (e) => handleSelectedFiles(Array.from(e.target.files)));
        folderInput.addEventListener('change', (e) => handleSelectedFiles(Array.from(e.target.files)));

        btnClearQueue.addEventListener('click', () => {
            queueList.innerHTML = '';
            uploadQueue.style.display = 'none';
        });

        if (btnCleanCache) {
            btnCleanCache.addEventListener('click', async () => {
                if (confirm('Empty trash bin and clear temporary upload cache?')) {
                    try {
                        const res = await fetch('/api/cache/purge', { method: 'POST' });
                        const data = await res.json();
                        if (data.success) {
                            showToast(`Reclaimed ${data.reclaimed_formatted} storage!`, 'success');
                            loadStorageInfo();
                            loadFilesList();
                        } else {
                            showToast(data.error || 'Purge failed', 'error');
                        }
                    } catch (err) {
                        showToast('Error cleaning cache', 'error');
                    }
                }
            });
        }

        // Drag & Drop

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        dropZone.addEventListener('drop', (e) => {
            const files = Array.from(e.dataTransfer.files);
            handleSelectedFiles(files);
        });

        // Search & Category Filters
        searchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value;
            renderFiles();
        });

        pillButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                pillButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentCategory = btn.dataset.category;
                renderFiles();
            });
        });

        // Modals
        closeVideoBtn.addEventListener('click', closeVideoModal);
        closeImageBtn.addEventListener('click', () => imageModal.style.display = 'none');
        closeAudioBtn.addEventListener('click', closeAudioModal);

        videoModal.addEventListener('click', (e) => { if (e.target === videoModal) closeVideoModal(); });
        imageModal.addEventListener('click', (e) => { if (e.target === imageModal) imageModal.style.display = 'none'; });
        audioModal.addEventListener('click', (e) => { if (e.target === audioModal) closeAudioModal(); });
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleSelectedFiles(files) {
        if (!files || files.length === 0) return;
        uploadQueue.style.display = 'block';

        let totalBytes = files.reduce((acc, f) => acc + f.size, 0);
        queueOverallStats.textContent = `Batch Total: ${formatBytes(totalBytes)} (${files.length} items)`;

        files.forEach(file => uploadFileInChunks(file));
    }

    async function uploadFileInChunks(file) {
        const uploadId = 'up_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

        // Create UI Queue Card
        const queueItem = document.createElement('div');
        queueItem.className = 'queue-item';
        queueItem.id = `q_${uploadId}`;
        queueItem.innerHTML = `
            <div class="queue-info">
                <span class="queue-file-title" title="${escapeHTML(file.name)}">${escapeHTML(file.name)} (${formatBytes(file.size)})</span>
                <div class="queue-badges">
                    <span class="badge-speed" id="speed_${uploadId}">0 MB/s</span>
                    <span class="badge-eta" id="eta_${uploadId}">Calculating...</span>
                    <span class="badge-status" id="percent_${uploadId}">0%</span>
                </div>
            </div>
            <div class="queue-progress-bar">
                <div class="queue-progress-fill" id="bar_${uploadId}" style="width: 0%;"></div>
            </div>
        `;
        queueList.appendChild(queueItem);

        const fillBar = document.getElementById(`bar_${uploadId}`);
        const percentTxt = document.getElementById(`percent_${uploadId}`);
        const speedTxt = document.getElementById(`speed_${uploadId}`);
        const etaTxt = document.getElementById(`eta_${uploadId}`);

        let startTime = Date.now();
        let bytesUploaded = 0;

        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
            const start = chunkIndex * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunkBlob = file.slice(start, end);

            const formData = new FormData();
            formData.append('chunk', chunkBlob);
            formData.append('upload_id', uploadId);
            formData.append('filename', file.name);
            formData.append('chunk_index', chunkIndex);
            formData.append('total_chunks', totalChunks);

            try {
                const response = await fetch('/api/upload/chunk', {
                    method: 'POST',
                    body: formData
                });
                const res = await response.json();

                if (!res.success) {
                    throw new Error(res.error || 'Chunk upload error');
                }

                bytesUploaded += (end - start);
                const percent = Math.round((bytesUploaded / file.size) * 100);
                fillBar.style.width = `${percent}%`;
                percentTxt.textContent = `${percent}%`;

                // Calculate Speed & ETA
                const elapsedTime = (Date.now() - startTime) / 1000;
                const speed = bytesUploaded / elapsedTime; // Bytes/sec
                const remainingBytes = file.size - bytesUploaded;
                const etaSeconds = speed > 0 ? Math.ceil(remainingBytes / speed) : 0;

                speedTxt.textContent = `${formatBytes(speed)}/s`;
                etaTxt.textContent = percent === 100 ? 'Completed' : `ETA: ${formatETA(etaSeconds)}`;

            } catch (err) {
                speedTxt.textContent = 'Failed';
                etaTxt.textContent = '';
                percentTxt.textContent = 'Error';
                fillBar.style.background = 'var(--accent-rose)';
                showToast(`Failed uploading ${file.name}`, 'error');
                return;
            }
        }

        // Upload Complete
        fillBar.style.background = 'var(--accent-emerald)';
        speedTxt.textContent = '✓ Done';
        etaTxt.textContent = '';
        showToast(`Uploaded ${file.name} successfully!`, 'success');
        
        loadFilesList();
        loadStorageInfo();
    }

    async function deleteFile(fileName) {
        try {
            const response = await fetch(`/api/files/${encodeURIComponent(fileName)}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                showToast(`Deleted ${fileName}`, 'success');
                loadFilesList();
                loadStorageInfo();
            } else {
                showToast(data.error || 'Failed to delete file', 'error');
            }
        } catch (err) {
            showToast('Error deleting file', 'error');
        }
    }

    function openVideoModal(fileName) {
        const fileObj = state.files.find(f => f.name === fileName);
        videoTitle.textContent = fileName;
        videoInfo.textContent = fileObj ? fileObj.formatted_size : '';
        videoDownload.href = `/download/${encodeURIComponent(fileName)}`;
        
        const streamUrl = `${window.location.origin}/files/${encodeURIComponent(fileName)}`;
        const transcodeUrl = `${window.location.origin}/transcode/${encodeURIComponent(fileName)}`;
        
        videoPlayer.src = streamUrl;
        videoPlayer.playbackRate = 1.0;
        
        // Reset active speed button
        document.querySelectorAll('.btn-speed').forEach(b => {
            b.classList.toggle('active', b.dataset.speed === '1.0');
        });

        // Audio Fix Transcode Button
        const btnTranscode = document.getElementById('btn-transcode-audio');
        if (btnTranscode) {
            btnTranscode.onclick = () => {
                showToast('Switching to AAC Audio Transcode Mode...', 'success');
                videoPlayer.src = transcodeUrl;
                videoPlayer.play().catch(e => console.log('Autoplay:', e));
            };
        }

        // External Player Button (VLC / MX Player Universal Launcher)
        const btnExternal = document.getElementById('btn-open-external');
        if (btnExternal) {
            btnExternal.onclick = () => {
                const ua = navigator.userAgent || '';
                const isAndroid = /android/i.test(ua);
                const isIOS = /iphone|ipad|ipod/i.test(ua);
                const rawHost = window.location.host;
                const encodedFile = encodeURIComponent(fileName);
                const streamUrl = `${window.location.origin}/files/${encodedFile}`;
                const m3uUrl = `${window.location.origin}/m3u/${encodedFile}`;

                if (isAndroid) {
                    // Launch Android VLC Intent
                    const intentUrl = `intent://${rawHost}/files/${encodedFile}#Intent;scheme=http;type=video/*;package=org.videolan.vlc;end`;
                    window.location.href = intentUrl;
                } else if (isIOS) {
                    // Launch iOS VLC Scheme
                    window.location.href = `vlc-x-callback://x-callback-url/stream?url=${encodeURIComponent(streamUrl)}`;
                } else {
                    // Trigger .m3u stream playlist download for VLC on Desktop
                    window.location.href = m3uUrl;
                }

                // Clipboard fallback for manual network stream pasting
                setTimeout(() => {
                    navigator.clipboard.writeText(streamUrl);
                    showToast('Opening in VLC & stream link copied to clipboard!', 'success');
                }, 600);
            };
        }


        // Error fallback for unsupported codecs
        videoPlayer.onerror = () => {
            showToast('Codec warning: Click "Fix Sound" or "Open in VLC"', 'error');
        };

        videoModal.style.display = 'flex';
        videoPlayer.play().catch(e => console.log('Autoplay policy: user interaction required', e));
    }


    function closeVideoModal() {
        videoPlayer.pause(); 
        videoPlayer.src = ''; 
        videoModal.style.display = 'none';
    }

    // Attach speed selector button listeners
    document.querySelectorAll('.btn-speed').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-speed').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const speed = parseFloat(btn.dataset.speed);
            if (videoPlayer) videoPlayer.playbackRate = speed;
        });
    });


    function openAudioModal(fileName) {
        audioTitle.textContent = fileName;
        audioPlayer.src = `/files/${encodeURIComponent(fileName)}`;
        audioModal.style.display = 'flex';
        audioPlayer.play().catch(e => console.log('Autoplay:', e));
    }

    function closeAudioModal() {
        audioPlayer.pause(); audioPlayer.src = ''; audioModal.style.display = 'none';
    }

    function openImageModal(fileName) {
        imageTitle.textContent = fileName;
        imagePreview.src = `/files/${encodeURIComponent(fileName)}`;
        imageModal.style.display = 'flex';
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatETA(seconds) {
        if (seconds <= 0) return '0s';
        if (seconds < 60) return `${seconds}s`;
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}m ${s}s`;
    }

    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠️'}</span> <span>${escapeHTML(message)}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
    }
});
