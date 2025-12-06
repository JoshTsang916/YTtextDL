const urlInput = document.getElementById('urlInput');
const submitBtn = document.getElementById('submitBtn');
const statusArea = document.getElementById('statusArea');
const statusText = document.getElementById('statusText');
const loader = document.querySelector('.loader');
const resultDetails = document.getElementById('resultDetails');
const videoTitle = document.getElementById('videoTitle');
const videoLang = document.getElementById('videoLang');
const chunkCount = document.getElementById('chunkCount');

submitBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) return;

    // Reset UI
    statusArea.classList.remove('hidden');
    resultDetails.classList.add('hidden');
    loader.classList.remove('hidden');
    statusText.textContent = "正在處理中，請稍候...";
    statusText.classList.remove('error-msg');
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '發生未知錯誤');
        }

        // Success
        loader.classList.add('hidden');
        statusText.textContent = "處理完成！";
        
        videoTitle.textContent = data.title;
        videoLang.textContent = data.language;
        chunkCount.textContent = data.chunks_count;
        
        resultDetails.classList.remove('hidden');

    } catch (error) {
        loader.classList.add('hidden');
        statusText.textContent = `錯誤: ${error.message}`;
        statusText.classList.add('error-msg');
    } finally {
        submitBtn.disabled = false;
    }
});

const qrBtn = document.getElementById('qrBtn');
const qrResult = document.getElementById('qrResult');
const qrImage = document.getElementById('qrImage');

qrBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) return;

    // Reset UI
    statusArea.classList.remove('hidden');
    resultDetails.classList.add('hidden');
    qrResult.classList.add('hidden');
    loader.classList.remove('hidden');
    statusText.textContent = "正在生成 QR Code...";
    statusText.classList.remove('error-msg');
    qrBtn.disabled = true;
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/qrcode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '發生未知錯誤');
        }

        // Success
        loader.classList.add('hidden');
        statusText.textContent = "QR Code 生成完成！";
        
        qrImage.src = data.qr_code;
        qrResult.classList.remove('hidden');

    } catch (error) {
        loader.classList.add('hidden');
        statusText.textContent = `錯誤: ${error.message}`;
        statusText.classList.add('error-msg');
    } finally {
        qrBtn.disabled = false;
        submitBtn.disabled = false;
    }
});
