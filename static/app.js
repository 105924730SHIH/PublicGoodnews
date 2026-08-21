(() => {
  "use strict";

  const fetchBtn = document.getElementById("fetch-btn");
  const sendBtn = document.getElementById("send-btn");
  const statusBox = document.getElementById("status-box");
  const previewBody = document.getElementById("preview-body");
  const tokenInput = document.getElementById("token-input");
  const chatIdInput = document.getElementById("chatid-input");

  let rawMessage = "";

  function setStatus(text) {
    statusBox.value = text;
  }

  function setBusy(btn, busy, busyLabel, idleLabel) {
    btn.disabled = busy;
    btn.textContent = busy ? busyLabel : idleLabel;
  }

  fetchBtn.addEventListener("click", async () => {
    setBusy(fetchBtn, true, "⏳ 抓取中...", "🔍 抓取最新資料");
    setStatus("正在抓取資料，請稍候...");

    try {
      const res = await fetch("/api/fetch", { method: "POST" });
      const data = await res.json();

      rawMessage = data.message || "";
      previewBody.innerHTML = data.preview_html || "（無內容）";
      setStatus(data.status || "");
    } catch (err) {
      setStatus(`❌ 抓取失敗：${err}`);
    } finally {
      setBusy(fetchBtn, false, "⏳ 抓取中...", "🔍 抓取最新資料");
    }
  });

  sendBtn.addEventListener("click", async () => {
    const token = tokenInput.value.trim();
    const chatId = chatIdInput.value.trim();

    if (!token) { setStatus("⚠️ 請先輸入 Telegram Bot Token"); return; }
    if (!chatId) { setStatus("⚠️ 請先輸入 Chat ID"); return; }
    if (!rawMessage) { setStatus("⚠️ 尚無可發送的內容，請先按下「抓取最新資料」"); return; }

    setBusy(sendBtn, true, "⏳ 發送中...", "🚀 發送到 Telegram");
    setStatus("正在發送到 Telegram...");

    try {
      const res = await fetch("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, chat_id: chatId, message: rawMessage }),
      });
      const data = await res.json();
      setStatus(data.status || "");
    } catch (err) {
      setStatus(`❌ 發送過程發生錯誤：${err}`);
    } finally {
      setBusy(sendBtn, false, "⏳ 發送中...", "🚀 發送到 Telegram");
    }
  });

  // ---------------------------------------------------------------------
  // 註冊 Service Worker
  // ---------------------------------------------------------------------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch((err) => {
        console.warn("Service worker 註冊失敗：", err);
      });
    });
  }

  // ---------------------------------------------------------------------
  // 安裝提示（beforeinstallprompt）
  // ---------------------------------------------------------------------
  const installBanner = document.getElementById("install-banner");
  const installBtn = document.getElementById("install-btn");
  const installDismiss = document.getElementById("install-dismiss");
  let deferredPrompt = null;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event;
    if (!localStorage.getItem("installBannerDismissed")) {
      installBanner.classList.remove("hidden");
    }
  });

  installBtn?.addEventListener("click", async () => {
    installBanner.classList.add("hidden");
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
  });

  installDismiss?.addEventListener("click", () => {
    installBanner.classList.add("hidden");
    localStorage.setItem("installBannerDismissed", "1");
  });

  window.addEventListener("appinstalled", () => {
    installBanner.classList.add("hidden");
  });
})();
