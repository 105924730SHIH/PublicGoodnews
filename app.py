"""
每日彙整快報 - PWA 版 (Flask 後端)
整合：公開資訊觀測站(MOPS)重大訊息 + 工商日報(CTEE)理財新聞
前端以 Progressive Web App (PWA) 形式呈現，可加到手機/桌面主畫面、離線開啟外殼畫面。

安裝套件：
    pip install -r requirements.txt

執行：
    python app.py
    （預設會開啟本機網址 http://127.0.0.1:5000）

⚠️ 安全提醒：
    Telegram Bot Token / Chat ID 只會在瀏覽器端記憶體與單次請求中使用，
    伺服器不會把它們寫入檔案或印到 log。
    請勿在公開場合分享畫面或截圖時把 Token 欄位曝光。
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import cloudscraper
from flask import Flask, jsonify, request, send_from_directory, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

# ========== emoji 池（依索引輪流使用，讓每則訊息不重複） ==========
EMOJI_MOPS = ["📢", "📌", "🔔", "📋", "🏢", "📑", "🗂️", "📎", "🔎", "🧾"]
EMOJI_NEWS = ["📰", "🗞️", "💹", "📈", "💰", "🔥", "🌐", "🧭", "⚡", "🪙"]


# ========== 資料抓取 ==========

def fetch_mops(limit: int = 10) -> pd.DataFrame:
    """抓取公開資訊觀測站重大訊息，取前 limit 筆。
    ⚠️ 若該頁面是前端 JS 動態渲染，requests 抓到的可能是空殼 HTML，
    屆時需改用該站的資料 API 或 Selenium/Playwright。"""
    url = "https://mopsov.twse.com.tw/mops/web/t05sr01_1"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://mopsov.twse.com.tw/mops/web/index",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    records = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            texts = [c.get_text(strip=True) for c in cells]
            if len(texts) >= 5 and texts[0].isdigit() and len(texts[0]) == 4:
                link_tag = row.find("a", href=True)
                if link_tag:
                    href = link_tag["href"]
                    detail_link = href if href.startswith("http") else \
                        "https://mopsov.twse.com.tw" + href
                else:
                    detail_link = url

                records.append({
                    "公司代號": texts[0],
                    "公司簡稱": texts[1],
                    "發言日期": texts[2],
                    "發言時間": texts[3],
                    "主旨": texts[4],
                    "連結": detail_link,
                })
            if len(records) >= limit:
                break
        if len(records) >= limit:
            break

    return pd.DataFrame(records[:limit],
                         columns=["公司代號", "公司簡稱", "發言日期", "發言時間", "主旨", "連結"])


def fetch_ctee(limit: int = 10) -> pd.DataFrame:
    """用 cloudscraper 抓取工商時報理財頭條 RSS，取前 limit 筆。"""
    rss_url = "https://www.ctee.com.tw/rss_web/category/we-highlights"
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    resp = scraper.get(rss_url, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "xml")

    records = []
    for item in soup.find_all("item")[:limit]:
        title = item.find("title").get_text(strip=True) if item.find("title") else ""
        link = item.find("link").get_text(strip=True) if item.find("link") else ""
        pub_date = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""
        records.append({"時間": pub_date, "標題": title, "連結": link})

    return pd.DataFrame(records)


# ========== 訊息組裝 ==========

def escape_html(text) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_message(mops_records, ctee_records) -> str:
    """組成附 emoji + 超連結的 HTML 格式訊息（給 Telegram 用）。"""
    lines = ["📊 <b>每日彙整快報</b> 📊", ""]

    lines.append(f"<b>【公開資訊觀測站 重大訊息 Top{len(mops_records)}】</b>")
    if not mops_records:
        lines.append("（今日無資料，或頁面結構有變動）")
    for i, row in enumerate(mops_records):
        emoji = EMOJI_MOPS[i % len(EMOJI_MOPS)]
        subject = escape_html(row["主旨"])
        company = escape_html(f"{row['公司代號']} {row['公司簡稱']}")
        link = row.get("連結", "")
        lines.append(
            f'{emoji} <a href="{link}">[{company}] {row["發言日期"]} {row["發言時間"]}</a>\n'
            f"　{subject}"
        )

    lines.append("")
    lines.append(f"<b>【工商日報 理財頭條 Top{len(ctee_records)}】</b>")
    if not ctee_records:
        lines.append("（今日無資料，或 RSS 來源有變動）")
    for i, row in enumerate(ctee_records):
        emoji = EMOJI_NEWS[i % len(EMOJI_NEWS)]
        title = escape_html(row["標題"])
        link = row.get("連結", "")
        lines.append(f'{emoji} <a href="{link}">{title}</a>')

    return "\n".join(lines)


# ========== Telegram 發送 ==========

def send_telegram(text: str, token: str, chat_id: str) -> list:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]

    results = []
    for chunk in chunks:
        resp = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        results.append(resp.json())
    return results


# ========== 頁面路由 ==========

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    # 放在根目錄回應，讓 service worker 的 scope 涵蓋整個網站
    return send_from_directory(".", "sw.js", mimetype="application/javascript")


@app.route("/icons/<path:filename>")
def icons(filename):
    return send_from_directory("icons", filename)


# ========== API 路由 ==========

@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """抓取 MOPS + CTEE 資料，回傳 JSON 給前端渲染預覽。"""
    data = request.get_json(silent=True) or {}
    mops_count = int(data.get("mops_count", 10))
    ctee_count = int(data.get("ctee_count", 10))

    try:
        mops_df = fetch_mops(mops_count)
    except Exception as e:
        return jsonify({"ok": False, "error": f"抓取 MOPS 時發生錯誤：{e}"}), 200

    try:
        ctee_df = fetch_ctee(ctee_count)
    except Exception as e:
        return jsonify({"ok": False, "error": f"抓取 CTEE 時發生錯誤：{e}"}), 200

    return jsonify({
        "ok": True,
        "mops": mops_df.to_dict(orient="records"),
        "ctee": ctee_df.to_dict(orient="records"),
    })


@app.route("/api/send", methods=["POST"])
def api_send():
    """用前端傳回來的已抓取資料組訊息並發送到 Telegram。"""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    chat_id = str(data.get("chat_id") or "").strip()
    mops_records = data.get("mops") or []
    ctee_records = data.get("ctee") or []

    if not token:
        return jsonify({"ok": False, "error": "請先輸入 Telegram Bot Token"})
    if not chat_id:
        return jsonify({"ok": False, "error": "請先輸入 Chat ID"})
    if not mops_records and not ctee_records:
        return jsonify({"ok": False, "error": "請先按「抓取並預覽」取得資料，再發送"})

    try:
        message = build_message(mops_records, ctee_records)
        results = send_telegram(message, token, chat_id)
    except Exception as e:
        return jsonify({"ok": False, "error": f"發送時發生錯誤：{e}"})

    failed = [r for r in results if not r.get("ok")]
    if failed:
        return jsonify({"ok": False, "error": f"部分或全部訊息發送失敗：{failed}"})

    return jsonify({"ok": True, "message": f"成功發送 {len(results)} 則訊息到 Telegram！"})


if __name__ == "__main__":
    # debug=True 方便本機開發；正式部署請關閉並改用正式 WSGI server（如 gunicorn）
    app.run(host="0.0.0.0", port=5000, debug=True)
