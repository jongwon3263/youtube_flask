document.getElementById('download-form').addEventListener('submit', async function (e) {
    e.preventDefault();
    const url = e.target.url.value;
    document.getElementById('status').innerText = "🔄 다운로드 준비 중...";

    const response = await fetch('/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });

    const data = await response.json();

    if (data.download_url) {
        document.getElementById('status').innerHTML = `✅`;
    } else {
        document.getElementById('status').innerText = "❌ 오류 발생: " + data.error;
    }
});
