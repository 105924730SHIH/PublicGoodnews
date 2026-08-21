// 每日彙整快報 PWA - 前端邏輯
// 負責呼叫後端 API (/api/fetch, /api/send)、渲染預覽，以及註冊 Service Worker / 安裝提示。

let lastMops = null;
let lastCtee = null;

const el = (id) => document.getElementById(id);

function setStatus(text, kind) {
  const box = el("status-box");
  box.textContent = text;
  box.classList.remove("ok", "error");
  if (kind) box.classList.add(kind);
}

function setBusy(isBusy) {
  ["fetch-btn", "send-btn", "all-btn"].forEach((id) => {
    el(id).disabled = isBusy;
  });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderPreview(mops, ctee) {
  const container = el("preview");
  const mopsCount = mops ? mops.length : 0;
  const cteeCount = ctee ? ctee.length : 0;

  let html = `<div class="section-title">📢 公開資訊觀測站 重大訊息 Top${mopsCount}</div>`;
  if (!mops || mops.length === 0) {
    html += `<div class="empty">（今日無資料，或頁面結構有變動）</div>`;
  } else {
    mops.forEach((row) => {
      html += `
        <div class="item">
          <a href="${escapeHtml(row["連結"])}" target="_blank" rel="noopener">
            [${escapeHtml(row["公司代號"])} ${escapeHtml(row["公司簡稱"])}]
          </a>
          <span class="meta">${escapeHtml(row["發言日期"])} ${escapeHtml(row["發言時間"])}</span>
          <div class="subject">${escapeHtml(row["主旨"])}</div>
        </div>`;
    });
  }

  html += `<div class="section-title">📰 工商日報 理財頭條 Top${cteeCount}</div>`;
  if (!ctee || ctee.length === 0) {
    html += `<div class="empty">（今日無資料，或 RSS 來源有變動）</div>`;
  } else {
    ctee.forEach((row) => {
      html += `
        <div class="item">
          <a href="${escapeHtml(row["連結"])}" target="_blank" rel="noopener">${escapeHtml(row["標題"])}</a>
        </div>`;
    });
  }

  container.innerHTML = html;
}

async function doFetch() {
  setBusy(true);
  setStatus("⏳ 抓取資料中...");
  try {
    const mopsCount = el("mops-slider").value;
    const cteeCount = el("ctee-slider").value;

    const resp = await fetch("/api/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mops_count: mopsCount, ctee_count: cteeCount }),
    });
    const data = await resp.json();

    if (!data.ok) {
      setStatus(`❌ ${data.error}`, "error");
      return null;
    }

    lastMops = data.mops;
    lastCtee = data.ctee;
    renderPreview(lastMops, lastCtee);
    setStatus(`✅ 抓取完成：MOPS ${data.mops.length} 筆、CTEE ${data.ctee.length} 筆`, "ok");
    return data;
  } catch (err) {
    setStatus(`❌ 抓取資料時發生錯誤：${err}`, "error");
    return null;
  } finally {
    setBusy(false);
  }
}

async function doSend() {
  const token = el("token-input").value;
  const chatId = el("chatid-input").value;

  if (!token.trim()) {
    setStatus("❌ 請先輸入 Telegram Bot Token", "error");
    return;
  }
  if (!chatId.trim()) {
    setStatus("❌ 請先輸入 Chat ID", "error");
    return;
  }
  if (lastMops === null || lastCtee === null) {
    setStatus("⚠️ 請先點「抓取並預覽」取得資料，再發送", "error");
    return;
  }

  setBusy(true);
  setStatus("⏳ 發送到 Telegram 中...");
  try {
    const resp = await fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token: token,
        chat_id: chatId,
        mops: lastMops,
        ctee: lastCtee,
      }),
    });
    const data = await resp.json();
    if (data.ok) {
      setStatus(`🎉 ${data.message}`, "ok");
    } else {
      setStatus(`❌ ${data.error}`, "error");
    }
  } catch (err) {
    setStatus(`❌ 發送時發生錯誤：${err}`, "error");
  } finally {
    setBusy(false);
  }
}

async function doFetchAndSend() {
  const data = await doFetch();
  if (data && data.ok) {
    await doSend();
  }
}

function bindUI() {
  el("mops-slider").addEventListener("input", (e) => {
    el("mops-value").textContent = e.target.value;
  });
  el("ctee-slider").addEventListener("input", (e) => {
    el("ctee-value").textContent = e.target.value;
  });

  el("fetch-btn").addEventListener("click", doFetch);
  el("send-btn").addEventListener("click", doSend);
  el("all-btn").addEventListener("click", doFetchAndSend);
}

// ========== PWA: Service Worker 註冊 ==========
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch((err) => {
        console.warn("Service worker 註冊失敗：", err);
      });
    });
  }
}

// ========== PWA: 自訂安裝提示 ==========
let deferredInstallPrompt = null;

function bindInstallPrompt() {
  const banner = el("install-banner");
  const installBtn = el("install-btn");
  const dismissBtn = el("dismiss-install-btn");

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    banner.style.display = "flex";
  });

  installBtn.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    banner.style.display = "none";
  });

  dismissBtn.addEventListener("click", () => {
    banner.style.display = "none";
  });

  window.addEventListener("appinstalled", () => {
    banner.style.display = "none";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  bindInstallPrompt();
  registerServiceWorker();
});
