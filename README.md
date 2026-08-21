# 每日資訊整理 · Telegram 推播（PWA 版）

從原本的 Gradio 版本改寫為 **Flask + PWA** 架構，可安裝到手機／桌面主畫面，並支援離線開啟介面。

## 資料夾結構

```
telegram_news_pwa/
├── app.py              # Flask 主程式（網頁 + API 路由 + 爬蟲 + Telegram 發送邏輯）
├── gen_icons.py         # 產生 icons/ 內各尺寸 PWA 圖示的腳本
├── requirements.txt     # 相依套件
├── manifest.json        # PWA 應用程式清單
├── sw.js                 # Service Worker（App Shell 快取，支援離線開啟介面）
├── icons/                # PWA 圖示（由 gen_icons.py 產生，已內附）
├── templates/
│   └── index.html        # 前端頁面
└── static/
    ├── style.css
    └── app.js             # 前端邏輯（呼叫 API、註冊 Service Worker、安裝提示）
```

## 安裝與執行

```bash
pip install -r requirements.txt

# 若要重新產生圖示（非必要，icons/ 內已附上產出結果）
python gen_icons.py

# 啟動伺服器
python app.py
```

開啟瀏覽器造訪 `http://127.0.0.1:5000`。

## 安裝為 PWA

- **Android / 桌面 Chrome**：開啟網頁後，畫面上方會出現「安裝」提示橫幅，或點瀏覽器網址列的安裝圖示。
- **iOS Safari**：點選「分享」→「加入主畫面」。

安裝後即可像原生 App 一樣從主畫面啟動，離線時仍可開啟介面外觀（實際抓取資料 / 發送訊息仍需網路連線）。

## 部署提醒

- 目前使用 Flask 內建開發伺服器（`app.run(debug=True)`），正式上線請改用 `gunicorn` 等 WSGI 伺服器，並關閉 debug 模式。
- `manifest.json` 與 `sw.js` 必須從網站**根目錄**提供（本專案已透過 Flask 路由處理），才能讓 Service Worker 的 scope 涵蓋整個網站。
- 若要部署到正式網域，PWA 安裝與 Service Worker 皆要求網站使用 **HTTPS**（`localhost` 開發時例外）。
- Telegram Bot Token／Chat ID 僅於發送當下由前端傳送給後端，後端不做任何儲存。
