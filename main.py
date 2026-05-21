"""
校园通知爬虫 + 推送系统
适配成都理工大学（CDUT）教务处 + 机电工程学院
使用持久化 Chrome 用户目录绕过 WAF
"""
import yaml
import os
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from notifier import EmailSender, DingTalkSender
from storage import filter_new_notices

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "cdut-chrome-profile")


def load_config():
    """加载配置文件，并用环境变量覆盖敏感字段"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 用环境变量覆盖敏感配置（优先级高于 config.yaml）
    channels = config.get("channels", {})

    email_cfg = channels.get("email", {})
    if os.getenv("EMAIL_SENDER"):
        email_cfg["sender_email"] = os.getenv("EMAIL_SENDER")
    if os.getenv("EMAIL_PASSWORD"):
        email_cfg["sender_password"] = os.getenv("EMAIL_PASSWORD")
    if os.getenv("EMAIL_RECIPIENTS"):
        email_cfg["recipients"] = [
            r.strip() for r in os.getenv("EMAIL_RECIPIENTS").split(",") if r.strip()
        ]

    dt_cfg = channels.get("dingtalk", {})
    if os.getenv("DINGTALK_WEBHOOK"):
        dt_cfg["webhook"] = os.getenv("DINGTALK_WEBHOOK")
    if os.getenv("DINGTALK_SECRET"):
        dt_cfg["secret"] = os.getenv("DINGTALK_SECRET")

    fs_cfg = channels.get("feishu", {})
    if os.getenv("FEISHU_WEBHOOK"):
        fs_cfg["webhook"] = os.getenv("FEISHU_WEBHOOK")

    return config


def scrape_site(context, target):
    """爬取单个网站的所有通知列表页"""
    name = target["name"]
    base_url = target["base_url"]
    link_patterns = target.get("link_patterns", [])
    all_notices = []

    for lp in target["list_pages"]:
        url = lp["url"]
        section = lp.get("section", "")
        try:
            print(f"  爬取: {url}")
            page = context.new_page()
            page.goto(url, wait_until="load", timeout=30000)
            page.wait_for_timeout(3000)

            soup = BeautifulSoup(page.content(), "html.parser")
            page.close()

            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                title = a.get_text(strip=True)

                # 检查是否是通知链接
                if not any(p in href for p in link_patterns):
                    continue
                if not title or len(title) < 4:
                    continue

                # 补全URL
                if href.startswith("../"):
                    full_url = "/".join(base_url.rstrip("/").split("/")[:-1]) + href[2:]
                elif href.startswith("/"):
                    full_url = base_url.rstrip("/") + href
                elif not href.startswith("http"):
                    full_url = base_url.rstrip("/") + "/" + href
                else:
                    full_url = href

                # 提取日期（从父元素 li 中的 span）
                date_str = ""
                parent = a.parent
                if parent:
                    spans = parent.find_all("span")
                    for s in spans:
                        t = s.get_text(strip=True)
                        if re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", t):
                            date_str = t
                            break

                if not date_str:
                    date_str = "未知"

                all_notices.append({
                    "title": title,
                    "url": full_url,
                    "date": date_str,
                    "source": name,
                    "section": section,
                })

        except Exception as e:
            print(f"  [ERROR] {url}: {e}")

    return all_notices


def main():
    print("=" * 50)
    print(f"  校园通知爬虫 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    config = load_config()
    lookback = config.get("schedule", {}).get("lookback_days", 1)
    cutoff = datetime.now() - timedelta(days=lookback)

    # 使用持久化 Chrome 用户目录（保持 WAF Cookie）
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=False,  # 需要可见窗口，WAF 才放行
            viewport={"width": 1920, "height": 1080},
            args=["--disable-blink-features=AutomationControlled"],
        )

        all_notices = []
        for target in config["targets"]:
            notices = scrape_site(context, target)
            recent = []
            for n in notices:
                if n["date"] != "未知":
                    try:
                        nd = datetime.strptime(n["date"].replace("/", "-"), "%Y-%m-%d")
                        if nd >= cutoff:
                            recent.append(n)
                    except ValueError:
                        pass
                else:
                    recent.append(n)
            print(f"[{target['name']}] {len(notices)}条, 近{lookback}天{len(recent)}条")
            all_notices.extend(recent)

        context.close()

    if not all_notices:
        print("无新通知。")
        return

    # 去重
    new_notices = filter_new_notices(all_notices)
    print(f"去重后: {len(new_notices)}条新通知")

    if not new_notices:
        print("全部已推送过。")
        return

    # 推送
    channels = config.get("channels", {})
    email_cfg = channels.get("email", {})
    if email_cfg.get("enabled"):
        EmailSender(email_cfg).send(new_notices)

    dt_cfg = channels.get("dingtalk", {})
    if dt_cfg.get("enabled"):
        DingTalkSender(dt_cfg).send(new_notices)

    print("完成！")


if __name__ == "__main__":
    main()
