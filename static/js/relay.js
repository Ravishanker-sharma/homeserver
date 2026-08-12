/**
 * Nexus Gate - Port 6969 Client JS
 */

document.addEventListener('DOMContentLoaded', () => {
    const authOverlay = document.getElementById('auth-overlay');
    const authForm = document.getElementById('auth-form');
    const passcodeInput = document.getElementById('passcode-input');
    const authError = document.getElementById('auth-error');
    const portalContent = document.getElementById('portal-content');
    const btnLogout = document.getElementById('btn-logout');

    const resolveForm = document.getElementById('resolve-form');
    const targetUrlInput = document.getElementById('target-url');
    const btnFetch = document.getElementById('btn-fetch');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    const resultContainer = document.getElementById('result-container');
    const resultFilename = document.getElementById('result-filename');
    const resultFilesize = document.getElementById('result-filesize');
    const resultIcon = document.getElementById('result-icon');
    const previewArea = document.getElementById('preview-area');
    const videoPlayer = document.getElementById('relay-video-player');
    const audioPlayer = document.getElementById('relay-audio-player');
    const imagePreview = document.getElementById('relay-image-preview');
    const downloadBtn = document.getElementById('result-download-btn');
    const copyPayloadBtn = document.getElementById('btn-copy-payload');

    let currentPayloadUrl = '';

    // ==========================================
    // AUTHENTICATION LOGIC
    // ==========================================
    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const passcode = passcodeInput.value.trim();
            authError.style.display = 'none';

            try {
                const response = await fetch('/api/auth', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ passcode })
                });

                const data = await response.json();
                if (data.success) {
                    authOverlay.style.display = 'none';
                    portalContent.style.display = 'block';
                    showToast('Gate Unlocked Successfully', 'success');
                } else {
                    authError.textContent = data.error || 'Access Denied: Incorrect Passcode';
                    authError.style.display = 'block';
                }
            } catch (err) {
                authError.textContent = 'Server connection error';
                authError.style.display = 'block';
            }
        });
    }

    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            await fetch('/api/logout', { method: 'POST' });
            window.location.reload();
        });
    }

    // ==========================================
    // LINK RESOLUTION LOGIC
    // ==========================================
    if (resolveForm) {
        resolveForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = targetUrlInput.value.trim();
            if (!url) return;

            setLoading(true);
            resultContainer.style.display = 'none';
            resetPreview();

            try {
                const response = await fetch('/api/resolve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                const data = await response.json();
                if (data.success) {
                    if (data.status === 'downloading') {
                        showToast('Downloading isolated asset to Vault...', 'success');
                        btnText.textContent = 'Downloading...';
                        btnSpinner.style.display = 'inline-block';
                        
                        const pollTask = setInterval(async () => {
                            const statusRes = await fetch(`/api/relay/status/${data.task_id}`);
                            const statusData = await statusRes.json();
                            
                            if (statusData.status === 'completed') {
                                clearInterval(pollTask);
                                showToast('Download complete! Asset added to Vault.', 'success');
                                setLoading(false);
                                btnText.textContent = 'Process Link';
                                fetchVaultFiles();
                            } else if (statusData.status === 'error') {
                                clearInterval(pollTask);
                                showToast('Download failed: ' + statusData.error, 'error');
                                setLoading(false);
                                btnText.textContent = 'Process Link';
                            } else {
                                btnText.textContent = `Downloading... ${statusData.progress || 0}%`;
                            }
                        }, 2000);
                        return; // Don't reset loading state yet
                    } else {
                        renderResult(data);
                        showToast('Asset resolved successfully!', 'success');
                    }
                } else {
                    showToast(data.error || 'Failed to resolve link', 'error');
                }
            } catch (err) {
                showToast('Error connecting to relay node', 'error');
            }
            if (btnText.textContent !== 'Downloading...') setLoading(false);
        });
    }

    function renderResult(data) {
        currentPayloadUrl = data.download_url || data.direct_url || data.url;
        resultFilename.textContent = data.filename || 'Resolved Payload Asset';
        resultFilesize.textContent = data.formatted_size || data.size || 'Direct Link Ready';
        
        downloadBtn.href = currentPayloadUrl;

        // Preview Media Handling
        const cat = data.category || 'other';
        previewArea.style.display = 'block';

        if (cat === 'video' || (currentPayloadUrl.includes('.mp4') || currentPayloadUrl.includes('.mkv'))) {
            resultIcon.textContent = '🎬';
            videoPlayer.style.display = 'block';
            videoPlayer.src = currentPayloadUrl;
            videoPlayer.play().catch(e => console.log('Autoplay blocked:', e));
        } else if (cat === 'audio' || (currentPayloadUrl.includes('.mp3') || currentPayloadUrl.includes('.wav'))) {
            resultIcon.textContent = '🎵';
            audioPlayer.style.display = 'block';
            audioPlayer.src = currentPayloadUrl;
            audioPlayer.play().catch(e => console.log('Autoplay blocked:', e));
        } else if (cat === 'image' || (currentPayloadUrl.includes('.jpg') || currentPayloadUrl.includes('.png'))) {
            resultIcon.textContent = '🖼️';
            imagePreview.style.display = 'block';
            imagePreview.src = currentPayloadUrl;
        } else {
            resultIcon.textContent = '📦';
            previewArea.style.display = 'none';
        }

        resultContainer.style.display = 'block';
    }

    if (copyPayloadBtn) {
        copyPayloadBtn.addEventListener('click', () => {
            if (currentPayloadUrl) {
                navigator.clipboard.writeText(currentPayloadUrl);
                showToast('Direct URL copied to clipboard!', 'success');
            }
        });
    }

    function resetPreview() {
        videoPlayer.pause(); videoPlayer.src = ''; videoPlayer.style.display = 'none';
        audioPlayer.pause(); audioPlayer.src = ''; audioPlayer.style.display = 'none';
        imagePreview.src = ''; imagePreview.style.display = 'none';
        previewArea.style.display = 'none';
    }

    function setLoading(isLoading) {
        btnSpinner.style.display = isLoading ? 'inline-block' : 'none';
        btnText.textContent = isLoading ? 'Processing...' : 'Process Link';
        btnFetch.disabled = isLoading;
        targetUrlInput.disabled = isLoading;
    }

    // ==========================================
    // VAULT MANAGEMENT
    // ==========================================
    
    async function fetchVaultFiles() {
        try {
            const res = await fetch('/api/relay/files');
            const data = await res.json();
            if (data.success) {
                renderVaultFiles(data.files);
            }
        } catch (e) {
            console.error('Failed to fetch vault', e);
        }
    }
    
    function renderVaultFiles(files) {
        const grid = document.getElementById('vault-grid');
        const emptyState = document.getElementById('vault-empty-state');
        if (!grid || !emptyState) return;
        
        grid.innerHTML = '';
        if (files.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        
        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        
        files.forEach(file => {
            const card = document.createElement('div');
            card.className = 'file-card';
            
            let icon = '📄';
            if (file.category === 'video') icon = '🎬';
            if (file.category === 'audio') icon = '🎵';
            if (file.category === 'image') icon = '🖼️';
            
            card.innerHTML = `
                <div class="file-icon">${icon}</div>
                <div class="file-info">
                    <h4 class="file-name" title="${file.name}">${file.name}</h4>
                    <p class="file-meta">${file.size}</p>
                </div>
                <div class="file-actions" style="margin-top: 10px; display: flex; gap: 5px;">
                    <button class="btn-primary btn-sm play-btn" style="flex:1;">Play</button>
                    <button class="btn-secondary btn-sm delete-btn" style="flex:1; background: #fee2e2; color: #dc2626; border-color: #fca5a5;">Delete</button>
                </div>
            `;
            
            const playBtn = card.querySelector('.play-btn');
            playBtn.onclick = () => {
                renderResult({
                    success: true,
                    download_url: file.url,
                    filename: file.name,
                    formatted_size: file.size,
                    category: file.category
                });
                window.scrollTo({ top: 0, behavior: 'smooth' });
            };
            
            const delBtn = card.querySelector('.delete-btn');
            delBtn.onclick = async () => {
                if (confirm('Delete this isolated asset forever?')) {
                    const res = await fetch(`/api/relay/files/${encodeURIComponent(file.name)}`, { method: 'DELETE' });
                    const d = await res.json();
                    if (d.success) {
                        showToast('Asset deleted', 'success');
                        fetchVaultFiles();
                        if (currentPayloadUrl === file.url) {
                            resetPreview();
                            resultContainer.style.display = 'none';
                        }
                    } else {
                        showToast('Failed to delete asset', 'error');
                    }
                }
            };
            
            grid.appendChild(card);
        });
    }
    
    // Fetch initial vault files if authenticated
    if (portalContent && portalContent.style.display !== 'none') {
        fetchVaultFiles();
    }

    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠️'}</span> <span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
});
