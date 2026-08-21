# 每日彙整快報 - PWA 版

將原本的 Gradio 介面改寫成 **Progressive Web App (PWA)**：Flask 後端 + 純 HTML/CSS/JS 前端，
可安裝到手機/桌面主畫面、有應用程式圖示、離線可開啟外殼畫面。

## 資料夾結構

```
daily_digest_pwa/
├── app.py                  # Flask 後端（抓資料 + 發送 Telegram 的 API）
├── requirements.txt        # Python 套件需求
├── gen_icons.py             # 產生 icons/ 資料夾內所有圖示的腳本
├── manifest.json            # PWA manifest
├── sw.js                    # Service Worker（離線快取應用外殼）
├── icons/                   # PWA 圖示（已預先產生好，可用 gen_icons.py 重新產生）
│   ├── icon-16.png ... icon-512.png
│   ├── icon-192-maskable.png / icon-512-maskable.png
│   └── favicon.ico
├── templates/
│   └── index.html            # PWA 主畫面
└── static/
    ├── css/style.css
    └── js/app.js
```

## 安裝與執行

```bash
pip install -r requirements.txt

# 若圖示需要重新產生（例如改了 gen_icons.py 的設計），可執行：
python gen_icons.py

python app.py
```

預設會在 `http://127.0.0.1:5000` 開啟服務。用手機瀏覽器打開這個網址（同一區網內用電腦
IP，例如 `http://192.168.x.x:5000`），瀏覽器會出現「加到主畫面」的提示，安裝後就會有獨立
的 App 圖示可以點擊開啟。

> 若要在正式環境部署，建議：
> 1. 使用正式的 WSGI Server（例如 `gunicorn app:app`）。
> 2. 部署在 HTTPS 網域下 —— PWA 的 Service Worker 與「加到主畫面」在正式環境需要 HTTPS
>    （`localhost` 開發時例外，瀏覽器允許 HTTP）。
> 3. 把 `app.py` 裡 `debug=True` 關閉。

## 使用方式

1. 開啟頁面後，先在「Telegram 設定」輸入你的 Bot Token 與 Chat ID。
2. 用滑桿調整想抓取的 MOPS / CTEE 筆數。
3. 按「🔍 抓取並預覽」先看看內容對不對，或按「⚡ 一鍵抓取並發送」直接推播到 Telegram。
4. Token 只會保留在瀏覽器分頁的記憶體與該次 API 請求中，伺服器不會寫入檔案或印到 log。

## PWA 重點說明

- **manifest.json**：定義 App 名稱、圖示、啟動畫面顏色、`display: standalone`（開啟後沒有
  瀏覽器網址列，看起來像原生 App）。
- **sw.js**：Service Worker，安裝時把 HTML/CSS/JS/圖示等「應用外殼」快取起來；`/api/` 開頭
  的資料請求一律走網路（不快取新聞資料，避免顯示過期內容）。
- **icons/**：包含各種尺寸圖示（含 maskable 版本，讓 Android 的自動遮罩形狀正常顯示）與
  `favicon.ico`；`gen_icons.py` 用 Pillow 純程式產生漸層背景 + 長條圖圖示，不需要額外美術
  素材即可重現或重新調整設計。
- 首次載入頁面時，右上角/畫面上方若瀏覽器判定符合安裝條件，會出現「📲 加到主畫面」提示列
  （對應 `beforeinstallprompt` 事件），可自訂觸發安裝流程。

## 與原本 Gradio 版本的差異

| 項目 | Gradio 版本 | PWA 版本 |
|---|---|---|
| 介面框架 | Gradio Blocks | Flask + 原生 HTML/CSS/JS |
| 執行方式 | `demo.launch()` 本機網頁 | Flask 伺服器 + 前端頁面 |
| 手機安裝 | 不支援 | 支援「加到主畫面」、獨立圖示、standalone 顯示模式 |
| 離線行為 | 無 | Service Worker 快取應用外殼，離線仍可開啟畫面 |
| 資料抓取/發送邏輯 | `fetch_mops` / `fetch_ctee` / `send_telegram` | 邏輯相同，搬到 Flask 的 `/api/fetch`、`/api/send` |
