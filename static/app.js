/**
 * IWantYT — Glassmorphism Light YouTube Downloader Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Element References
    const urlForm = document.getElementById('urlForm');
    const ytUrlInput = document.getElementById('ytUrlInput');
    const pasteBtn = document.getElementById('pasteBtn');
    const clearBtn = document.getElementById('clearBtn');
    const fetchBtn = document.getElementById('fetchBtn');
    const sampleChips = document.querySelectorAll('.sample-chip');

    const loaderCard = document.getElementById('loaderCard');
    const errorCard = document.getElementById('errorCard');
    const errorTitle = document.getElementById('errorTitle');
    const errorMsg = document.getElementById('errorMsg');
    const closeErrorBtn = document.getElementById('closeErrorBtn');

    const previewSection = document.getElementById('previewSection');
    const videoThumb = document.getElementById('videoThumb');
    const videoTitle = document.getElementById('videoTitle');
    const videoAuthor = document.getElementById('videoAuthor');
    const videoViews = document.getElementById('videoViews');
    const videoDuration = document.getElementById('videoDuration');
    const qualityGrid = document.getElementById('qualityGrid');
    const startDownloadBtn = document.getElementById('startDownloadBtn');

    const downloadProgressContainer = document.getElementById('downloadProgressContainer');
    const progressStatus = document.getElementById('progressStatus');
    const progressPercent = document.getElementById('progressPercent');
    const progressBarFill = document.getElementById('progressBarFill');

    const historyList = document.getElementById('historyList');
    const emptyHistoryMsg = document.getElementById('emptyHistoryMsg');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    // State Variables
    let currentVideoData = null;
    let selectedQualityId = 'highest';
    let historyState = JSON.parse(localStorage.getItem('iwantyt_history') || '[]');

    // Initialize Page
    renderHistory();
    toggleInputButtons();

    // Input Change & Paste Handling
    ytUrlInput.addEventListener('input', toggleInputButtons);
    
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                ytUrlInput.value = text.trim();
                toggleInputButtons();
                showToast('Pasted URL from clipboard!');
            }
        } catch (err) {
            showToast('Unable to read clipboard. Please paste manually.', true);
        }
    });

    clearBtn.addEventListener('click', () => {
        ytUrlInput.value = '';
        toggleInputButtons();
        ytUrlInput.focus();
    });

    // Sample Chips Click
    sampleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const url = chip.dataset.url;
            ytUrlInput.value = url;
            toggleInputButtons();
            fetchVideoInfo(url);
        });
    });

    // Form Submit
    urlForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const url = ytUrlInput.value.trim();
        if (url) {
            fetchVideoInfo(url);
        }
    });

    closeErrorBtn.addEventListener('click', () => {
        errorCard.classList.add('hidden');
    });

    // Fetch Video Metadata from API
    async function fetchVideoInfo(url) {
        // UI Reset
        hideAllCards();
        loaderCard.classList.remove('hidden');

        try {
            const response = await fetch(`/api/info?url=${encodeURIComponent(url)}`);
            const data = await response.json();

            if (!response.ok || data.status !== 'success') {
                throw new Error(data.detail || 'Could not fetch video info.');
            }

            currentVideoData = data;
            displayVideoPreview(data);
            loaderCard.classList.add('hidden');
            previewSection.classList.remove('hidden');

            // Scroll smoothly to preview card
            previewSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

        } catch (error) {
            loaderCard.classList.add('hidden');
            showError('Video Fetch Failed', error.message || 'Check your YouTube URL and internet connection.');
        }
    }

    // Display Preview & Streams Grid
    function displayVideoPreview(data) {
        videoThumb.src = data.thumbnail_url;
        videoTitle.textContent = data.title;
        videoAuthor.textContent = data.author;
        videoViews.textContent = data.views;
        videoDuration.textContent = data.duration;

        // Render Streams Grid
        qualityGrid.innerHTML = '';
        selectedQualityId = data.streams[0]?.id || 'highest';

        data.streams.forEach((stream, index) => {
            const option = document.createElement('div');
            option.className = `quality-option ${index === 0 ? 'selected' : ''}`;
            option.dataset.id = stream.id;

            option.innerHTML = `
                <span class="option-badge">${stream.badge}</span>
                <span class="option-label">${stream.label}</span>
            `;

            option.addEventListener('click', () => {
                document.querySelectorAll('.quality-option').forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');
                selectedQualityId = stream.id;
            });

            qualityGrid.appendChild(option);
        });
    }

    // Download Execution
    startDownloadBtn.addEventListener('click', async () => {
        if (!currentVideoData) return;

        const videoUrl = currentVideoData.url;
        const quality = selectedQualityId;

        // UI Progress State
        startDownloadBtn.disabled = true;
        downloadProgressContainer.classList.remove('hidden');
        progressStatus.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing & downloading on server...';
        progressPercent.textContent = '15%';
        progressBarFill.style.width = '30%';

        try {
            const downloadUrl = `/api/download?url=${encodeURIComponent(videoUrl)}&quality=${encodeURIComponent(quality)}`;
            
            progressPercent.textContent = '50%';
            progressBarFill.style.width = '65%';

            const response = await fetch(downloadUrl);
            
            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.detail || 'Download request failed.');
            }

            progressPercent.textContent = '85%';
            progressBarFill.style.width = '88%';

            // Get filename from response header if available
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `${currentVideoData.title}.${quality === 'audio' ? 'mp3' : 'mp4'}`;
            if (contentDisposition && contentDisposition.includes('filename=')) {
                const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
                if (matches && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }

            // Stream response to blob
            const blob = await response.blob();
            const blobUrl = window.URL.createObjectURL(blob);

            // Trigger browser save prompt
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(blobUrl);

            // Finish Progress
            progressPercent.textContent = '100%';
            progressBarFill.style.width = '100%';
            progressStatus.innerHTML = '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i> Download Complete!';

            // Save to Session History
            addHistoryItem({
                title: currentVideoData.title,
                url: currentVideoData.url,
                quality: quality.toUpperCase(),
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            });

            showToast('Download started! Check your downloads folder.');

            setTimeout(() => {
                startDownloadBtn.disabled = false;
            }, 1000);

        } catch (err) {
            downloadProgressContainer.classList.add('hidden');
            startDownloadBtn.disabled = false;
            showError('Download Error', err.message || 'An error occurred while generating your download.');
        }
    });

    // History Logic
    function addHistoryItem(item) {
        historyState.unshift(item);
        if (historyState.length > 10) historyState.pop();
        localStorage.setItem('iwantyt_history', JSON.stringify(historyState));
        renderHistory();
    }

    function renderHistory() {
        if (!historyState || historyState.length === 0) {
            emptyHistoryMsg.style.display = 'flex';
            return;
        }

        emptyHistoryMsg.style.display = 'none';
        const existingItems = historyList.querySelectorAll('.history-item');
        existingItems.forEach(el => el.remove());

        historyState.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.innerHTML = `
                <div class="history-details">
                    <div class="history-icon">
                        <i class="fa-solid ${item.quality.includes('MP3') || item.quality === 'AUDIO' ? 'fa-music' : 'fa-film'}"></i>
                    </div>
                    <div>
                        <div class="history-title-text">${item.title}</div>
                        <div class="history-meta">${item.quality} &bull; ${item.time}</div>
                    </div>
                </div>
                <button class="sample-chip" onclick="window.open('${item.url}', '_blank')">Watch <i class="fa-solid fa-up-right-from-square"></i></button>
            `;
            historyList.appendChild(historyItem);
        });
    }

    clearHistoryBtn.addEventListener('click', () => {
        historyState = [];
        localStorage.removeItem('iwantyt_history');
        renderHistory();
        showToast('History cleared.');
    });

    // Helper UI functions
    function toggleInputButtons() {
        if (ytUrlInput.value.length > 0) {
            clearBtn.classList.remove('hidden');
            pasteBtn.classList.add('hidden');
        } else {
            clearBtn.classList.add('hidden');
            pasteBtn.classList.remove('hidden');
        }
    }

    function hideAllCards() {
        loaderCard.classList.add('hidden');
        errorCard.classList.add('hidden');
        previewSection.classList.add('hidden');
    }

    function showError(title, message) {
        errorTitle.textContent = title;
        errorMsg.textContent = message;
        errorCard.classList.remove('hidden');
    }

    function showToast(msg, isError = false) {
        toastMessage.textContent = msg;
        const icon = toast.querySelector('i');
        if (isError) {
            icon.className = 'fa-solid fa-circle-xmark';
            icon.style.color = '#ef4444';
        } else {
            icon.className = 'fa-solid fa-circle-check';
            icon.style.color = '#10b981';
        }
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3500);
    }
});
