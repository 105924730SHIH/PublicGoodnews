"""
每日資訊整理 + Telegram 推播（PWA 版）
=================================================
功能：
1. 抓取「公開資訊觀測站」重大訊息公告，取前 10 筆（含公告連結）
2. 抓取「工商日報 - 理財新訊」，取前 10 筆（含新聞連結）
3. 整理成含 emoji 與超連結的訊息文字（Telegram HTML 格式）
4. 使用者於網頁介面輸入自己的 Telegram Bot Token 與 Chat ID，一鍵發送
5. 提供 manifest.json / service worker，可安裝為 PWA（支援離線開啟介面）

安裝套件：
    pip install -r requirements.txt

執行方式：
    python app.py
    # 預設於 http://127.0.0.1:5000 啟動
"""

import html
import random
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, send_from_directory, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------------------------------------------------------------------------
# 共用設定
# ---------------------------------------------------------------------------

COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

MOPS_BASE_URL = "https://mopsov.twse.com.tw"
CTEE_BASE_URL = "https://www.ctee.com.tw"

EMOJI_LIST = ["✨", "📌", "🔥", "📈", "💡", "🗞️", "✅", "🚀", "📊", "⭐"]


def random_emoji() -> str:
    return random.choice(EMOJI_LIST)


# ---------------------------------------------------------------------------
# 抓取：公開資訊觀測站
# ---------------------------------------------------------------------------

def fetch_mops_top10() -> pd.DataFrame:
    url = "https://mopsov.twse.com.tw/mops/web/t05sr01_1"
    headers = {**COMMON_HEADERS, "Referer": "https://mopsov.twse.com.tw/mops/web/index"}

    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    records = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            texts = [c.get_text(strip=True) for c in cells]

            if len(texts) >= 5 and texts[0].isdigit() and len(texts[0]) == 4:
                link_tag = row.find("a", href=True)
                link = urljoin(MOPS_BASE_URL, link_tag["href"]) if link_tag else url
                records.append({
                    "公司代號": texts[0],
                    "公司簡稱": texts[1],
                    "發言日期": texts[2],
                    "發言時間": texts[3],
                    "主旨": texts[4],
                    "連結": link,
                })

    df = pd.DataFrame(records, columns=["公司代號", "公司簡稱", "發言日期", "發言時間", "主旨", "連結"])
    return df.head(10)


# ---------------------------------------------------------------------------
# 抓取：工商日報
# ---------------------------------------------------------------------------

def fetch_ctee_top10() -> pd.DataFrame:
    url = "https://www.ctee.com.tw/wealth/we-highlights"

    resp = requests.get(url, headers=COMMON_HEADERS, timeout=10)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        soup = BeautifulSoup(resp.text, "html.parser")

    records = []
    for summary_tag in soup.find_all("p", class_="news-summary"):
        content = summary_tag.get_text(strip=True)

        container = summary_tag.find_parent(["li", "div", "article"])
        if container is None:
            container = summary_tag.parent

        title_tag = container.find("a", href=re.compile(r"/news/\d+"))
        title = title_tag.get_text(strip=True) if title_tag else None
        link = urljoin(CTEE_BASE_URL, title_tag["href"]) if title_tag else CTEE_BASE_URL

        category_tag = None
        for a in container.find_all("a", href=True):
            if re.match(r"^/[a-zA-Z\-]+$", a["href"]):
                category_tag = a
                break
        category = category_tag.get_text(strip=True) if category_tag else None

        time_tag = container.find(class_="news-time")
        time_text = time_tag.get_text(strip=True) if time_tag else None

        records.append({
            "時間": time_text,
            "類別": category,
            "標題": title,
            "內容": content,
            "連結": link,
        })

    df = pd.DataFrame(records, columns=["時間", "類別", "標題", "內容", "連結"])
    return df.head(10)


# ---------------------------------------------------------------------------
# 整理成含 emoji + 超連結的訊息文字（Telegram HTML 格式）
# ---------------------------------------------------------------------------

def _esc(text) -> str:
    return html.escape(str(text)) if text else ""


def build_message(mops_df: pd.DataFrame, ctee_df: pd.DataFrame) -> str:
    lines = [f"📢 <b>每日資訊整理</b> {random_emoji()}", ""]

    lines.append(f"【公開資訊觀測站 前10筆】{random_emoji()}")
    if mops_df.empty:
        lines.append("（今日無資料，或抓取失敗）")
    else:
        for i, row in enumerate(mops_df.itertuples(index=False), start=1):
            subject = _esc(row.主旨)
            lines.append(
                f'{i}. {random_emoji()} [{_esc(row.公司代號)} {_esc(row.公司簡稱)}] '
                f'{_esc(row.發言日期)} {_esc(row.發言時間)} '
                f'<a href="{_esc(row.連結)}">{subject}</a>'
            )

    lines.append("")
    lines.append(f"【工商日報 理財新訊 前10筆】{random_emoji()}")
    if ctee_df.empty:
        lines.append("（今日無資料，或抓取失敗）")
    else:
        for i, row in enumerate(ctee_df.itertuples(index=False), start=1):
            title = row.標題 or (row.內容[:20] if row.內容 else "（無標題）")
            time_text = row.時間 or ""
            category = row.類別 or ""
            lines.append(
                f'{i}. {random_emoji()} [{_esc(category)}] {_esc(time_text)} '
                f'<a href="{_esc(row.連結)}">{_esc(title)}</a>'
            )

    lines.append("")
    lines.append(f"以上，資料僅供參考 {random_emoji()}")

    return "\n".join(lines)


def message_to_preview_html(message: str) -> str:
    """把 Telegram 用的 HTML 訊息包裝成可在網頁中預覽的卡片內容（純內文，外層卡片由前端 CSS 負責）。"""
    return message.replace("\n", "<br>")


# ---------------------------------------------------------------------------
# Telegram 發送
# ---------------------------------------------------------------------------

def send_to_telegram(message: str, token: str, chat_id: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    results = []

    max_len = 4000
    chunks, current = [], ""
    for line in message.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > max_len:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    for chunk in chunks:
        resp = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        results.append(resp.json())

    return results


# ---------------------------------------------------------------------------
# 頁面路由（前端 UI + PWA 必要檔案）
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    # Service Worker 需從網站根目錄提供，且不建議被快取，才能及時抓到新版本
    response = send_from_directory(".", "sw.js", mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/icons/<path:filename>")
def icons(filename):
    return send_from_directory("icons", filename)


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------

@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    try:
        mops_df = fetch_mops_top10()
        mops_status = f"✅ 公開資訊觀測站：取得 {len(mops_df)} 筆"
    except Exception as e:
        mops_df = pd.DataFrame(columns=["公司代號", "公司簡稱", "發言日期", "發言時間", "主旨", "連結"])
        mops_status = f"❌ 公開資訊觀測站抓取失敗：{e}"

    try:
        ctee_df = fetch_ctee_top10()
        ctee_status = f"✅ 工商日報：取得 {len(ctee_df)} 筆"
    except Exception as e:
        ctee_df = pd.DataFrame(columns=["時間", "類別", "標題", "內容", "連結"])
        ctee_status = f"❌ 工商日報抓取失敗：{e}"

    message = build_message(mops_df, ctee_df)
    preview_html = message_to_preview_html(message)
    status = f"{mops_status}\n{ctee_status}"

    return jsonify({
        "preview_html": preview_html,
        "message": message,
        "status": status,
    })


@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    chat_id = (data.get("chat_id") or "").strip()
    message = (data.get("message") or "").strip()

    if not token:
        return jsonify({"status": "⚠️ 請先輸入 Telegram Bot Token"}), 400
    if not chat_id:
        return jsonify({"status": "⚠️ 請先輸入 Chat ID"}), 400
    if not message:
        return jsonify({"status": "⚠️ 尚無可發送的內容，請先按下「抓取最新資料」"}), 400

    try:
        results = send_to_telegram(message, token, chat_id)
    except Exception as e:
        return jsonify({"status": f"❌ 發送過程發生錯誤：{e}"}), 500

    ok = sum(1 for r in results if r.get("ok"))
    fail = len(results) - ok

    if fail == 0:
        return jsonify({"status": f"✅ 發送成功！共 {len(results)} 段訊息已送達。"})
    else:
        errors = [r.get("description", "未知錯誤") for r in results if not r.get("ok")]
        return jsonify({
            "status": f"⚠️ 共 {len(results)} 段，成功 {ok} 段，失敗 {fail} 段。\n錯誤訊息：{'; '.join(errors)}"
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
