/**
 * Termux StreamDrive & Storage Vault Client JS
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    let state = {
        files: [],
        currentCategory: 'all',
        searchQuery: '',
        storage: null
    };

    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const btnBrowse = document.getElementById('btn-browse');
    const uploadQueue = document.getElementById('upload-queue');
    const queueList = document.getElementById('queue-list');
    const uploadCount = document.getElementById('upload-count');
    
    const fileGrid = document.getElementById('file-grid');
    const emptyState = document.getElementById('empty-state');
    const searchInput = document.getElementById('search-input');
    const pillButtons = document.querySelectorAll('.pill-btn');
    
    // Storage elements
    const storageBar = document.getElementById('storage-bar');
    const storagePercent = document.getElementById('storage-percent');
    const statUsed = document.getElementById('stat-used');
    const statFree = document.getElementById('stat-free');
    const statTotal = document.getElementById('stat-total');
    const storageSub = document.getElementById('storage-status-sub');
    
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

    // Category Icons Map
    const categoryIcons = {
        video: '🎥',
        audio: '🎵',
        image: '🖼️',
        document: '📄',
        archive: '📦',
        other: '📎'
    };

    // ==========================================
    // INITIALIZATION & POLLING
    // ==========================================
    init();

    function init() {
        loadStorageInfo();
        loadFilesList();
        setupEventListeners();
        
        // Refresh storage metrics every 30 seconds
        setInterval(loadStorageInfo, 30000);
    }

    // ==========================================
    // API CALLS
    // ==========================================
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
            console.error('Failed to load file list:', err);
            showToast('Error loading file list', 'error');
        }
    }

    // ==========================================
    // RENDER FUNCTIONS
    // ==========================================
    function renderStorage(storage) {
        if (!storage) return;
        
        storageBar.style.width = `${storage.percent_used}%`;
        storagePercent.textContent = `${storage.percent_used}%`;
        statUsed.textContent = storage.used_formatted;
        statFree.textContent = storage.free_formatted;
        statTotal.textContent = storage.total_formatted;
        
        storageSub.textContent = `${storage.free_formatted} available space out of ${storage.total_formatted}`;
        
        // Highlight warning color if disk is > 85% full
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
        
        // Attach action handlers to dynamic buttons
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
            btn.addEventListener('click', (e) => {
                const encodedName = btn.dataset.file;
                const fileName = decodeURIComponent(encodedName);
                openVideoModal(fileName);
            });
        });

        document.querySelectorAll('[data-action="stream-audio"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const encodedName = btn.dataset.file;
                const fileName = decodeURIComponent(encodedName);
                openAudioModal(fileName);
            });
        });

        document.querySelectorAll('[data-action="preview-image"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const encodedName = btn.dataset.file;
                const fileName = decodeURIComponent(encodedName);
                openImageModal(fileName);
            });
        });

        document.querySelectorAll('[data-action="copy-link"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const url = btn.dataset.url;
                navigator.clipboard.writeText(url);
                showToast('Stream link copied to clipboard!', 'success');
            });
        });

        document.querySelectorAll('[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const encodedName = btn.dataset.file;
                const fileName = decodeURIComponent(encodedName);
                if (confirm(`Are you sure you want to delete "${fileName}"?`)) {
                    await deleteFile(fileName);
                }
            });
        });
    }

    // ==========================================
    // UPLOAD LOGIC
    // ==========================================
    function setupEventListeners() {
        // Browse button & File input
        btnBrowse.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => handleFilesSelect(e.target.files));

        // Drag and Drop
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
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFilesSelect(files);
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

        // Modal close buttons
        closeVideoBtn.addEventListener('click', closeVideoModal);
        closeImageBtn.addEventListener('click', () => imageModal.style.display = 'none');
        closeAudioBtn.addEventListener('click', closeAudioModal);

        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) closeVideoModal();
        });
        imageModal.addEventListener('click', (e) => {
            if (e.target === imageModal) imageModal.style.display = 'none';
        });
        audioModal.addEventListener('click', (e) => {
            if (e.target === audioModal) closeAudioModal();
        });
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleFilesSelect(filesList) {
        if (!filesList || filesList.length === 0) return;
        
        uploadQueue.style.display = 'block';
        uploadCount.textContent = `${filesList.length} item(s)`;
        queueList.innerHTML = '';
        
        uploadFiles(Array.from(filesList));
    }

    function uploadFiles(files) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        const queueItem = document.createElement('div');
        queueItem.className = 'queue-item';
        queueItem.innerHTML = `
            <div class="queue-info">
                <span>Uploading ${files.length} file(s)...</span>
                <span id="upload-percent">0%</span>
            </div>
            <div class="queue-progress-bar">
                <div class="queue-progress-fill" id="upload-progress-fill" style="width: 0%;"></div>
            </div>
        `;
        queueList.appendChild(queueItem);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                document.getElementById('upload-progress-fill').style.width = `${percent}%`;
                document.getElementById('upload-percent').textContent = `${percent}%`;
            }
        };

        xhr.onload = () => {
            if (xhr.status === 200) {
                const res = JSON.parse(xhr.responseText);
                if (res.success) {
                    showToast(`Uploaded ${files.length} file(s) successfully!`, 'success');
                    loadFilesList();
                    loadStorageInfo();
                    setTimeout(() => { uploadQueue.style.display = 'none'; }, 2000);
                } else {
                    showToast(res.error || 'Upload failed', 'error');
                }
            } else {
                showToast('Upload error occurred', 'error');
            }
        };

        xhr.onerror = () => showToast('Network connection error', 'error');
        xhr.send(formData);
    }

    // ==========================================
    // DELETE FILE
    // ==========================================
    async function deleteFile(fileName) {
        try {
            const response = await fetch(`/api/files/${encodeURIComponent(fileName)}`, {
                method: 'DELETE'
            });
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

    // ==========================================
    // MODAL CONTROL & MEDIA STREAMING
    // ==========================================
    function openVideoModal(fileName) {
        const fileObj = state.files.find(f => f.name === fileName);
        videoTitle.textContent = fileName;
        videoInfo.textContent = fileObj ? fileObj.formatted_size : '';
        videoDownload.href = `/download/${encodeURIComponent(fileName)}`;
        
        videoPlayer.src = `/files/${encodeURIComponent(fileName)}`;
        videoModal.style.display = 'flex';
        videoPlayer.play().catch(e => console.log('Autoplay prevented:', e));
    }

    function closeVideoModal() {
        videoPlayer.pause();
        videoPlayer.src = '';
        videoModal.style.display = 'none';
    }

    function openAudioModal(fileName) {
        audioTitle.textContent = fileName;
        audioPlayer.src = `/files/${encodeURIComponent(fileName)}`;
        audioModal.style.display = 'flex';
        audioPlayer.play().catch(e => console.log('Autoplay prevented:', e));
    }

    function closeAudioModal() {
        audioPlayer.pause();
        audioPlayer.src = '';
        audioModal.style.display = 'none';
    }

    function openImageModal(fileName) {
        imageTitle.textContent = fileName;
        imagePreview.src = `/files/${encodeURIComponent(fileName)}`;
        imageModal.style.display = 'flex';
    }

    // ==========================================
    // UTILS & TOASTS
    // ==========================================
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = type === 'success' ? '✓' : '⚠️';
        toast.innerHTML = `<span>${icon}</span> <span>${escapeHTML(message)}</span>`;
        
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }
});
