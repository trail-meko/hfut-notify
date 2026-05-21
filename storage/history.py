import json
import os

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "history.json")

def load_history():
    """加载已发送通知历史"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    """保存通知历史"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def filter_new_notices(notices):
    """
    过滤出新通知（去重）
    使用 URL 作为唯一标识
    """
    history = load_history()
    new_notices = []
    for n in notices:
        uid = n["url"]
        if uid not in history:
            history[uid] = {
                "title": n["title"],
                "date": n["date"],
                "source": n["source"],
                "section": n.get("section", ""),
            }
            new_notices.append(n)
    if new_notices:
        save_history(history)
    return new_notices
