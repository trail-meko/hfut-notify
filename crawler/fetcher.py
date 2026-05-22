"""
校园通知爬虫（Playwright 浏览器引擎 + stealth 隐身）
适配成都理工大学教务处 + 机电工程学院
因网站有 JS 反爬机制，使用真实浏览器 + 反检测补丁渲染后提取内容
"""
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta


class NoticeFetcher:
    """爬取校园网站通知列表（使用 Playwright 浏览器）"""

    def __init__(self, target_config, browser):
        self.name = target_config["name"]
        self.base_url = target_config.get("base_url", "")
        self.list_pages = target_config["list_pages"]
        self.link_patterns = target_config.get("link_patterns", [])
        self.browser = browser
        self.stealth = Stealth()

    def fetch_and_parse(self, url):
        """用 Playwright 打开页面（隐身模式），返回 BeautifulSoup"""
        page = self.browser.new_page()
        try:
            # 应用 stealth 补丁，隐藏自动化特征
            self.stealth.apply_stealth_sync(page)
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            if len(html) < 5000:
                print(f"  [WARN] {url} 可能被拦截，响应长度: {len(html)}")
            return BeautifulSoup(html, "html.parser")
        finally:
            page.close()

    def parse_notice_list(self, soup, page_url, section):
        """从页面中提取通知列表（使用通用策略）"""
        notices = []
        processed_urls = set()

        # 策略1：找所有 a 标签，过滤出通知链接
        all_links = soup.find_all("a", href=True)
        for a in all_links:
            href = a.get("href", "")
            title = a.get_text(strip=True)

            # 判断是否是通知链接
            is_notice = False
            if self.link_patterns:
                for pat in self.link_patterns:
                    if pat in href:
                        is_notice = True
                        break
            else:
                # 通用判断：链接包含 info/ 或 content.jsp
                if "info/" in href or "content.jsp" in href:
                    is_notice = True

            if not is_notice:
                continue
            if not title or len(title) < 4:
                continue
            if href in processed_urls:
                continue
            processed_urls.add(href)

            # 补全相对路径
            full_url = href
            if not href.startswith("http"):
                if href.startswith("../"):
                    # ../info/1171/xxxx.htm → 去掉一层目录
                    full_url = "/".join(self.base_url.rstrip("/").split("/")[:-1]) + href[2:]
                elif href.startswith("/"):
                    full_url = self.base_url.rstrip("/") + href
                else:
                    full_url = self.base_url.rstrip("/") + "/" + href

            # 提取日期
            date = None

            # 方法1：从父元素 <li> 中找 <span>（CDUT 教务处的格式）
            parent = a.parent
            if parent:
                spans = parent.find_all("span")
                for s in spans:
                    d = self._parse_date(s.get_text(strip=True))
                    if d:
                        date = d
                        break

            # 方法2：从标题文本末尾找日期（备用）
            if not date:
                d = self._parse_date(title)
                if d:
                    date = d

            notices.append({
                "title": title,
                "url": full_url,
                "date": date.strftime("%Y-%m-%d") if date else "未知",
                "source": self.name,
                "section": section,
            })

        return notices

    def get_all_notices(self, lookback_days=1):
        """获取所有列表页的当日通知"""
        all_notices = []
        cutoff = datetime.now() - timedelta(days=lookback_days)

        for list_page in self.list_pages:
            url = list_page["url"]
            section = list_page.get("section", "")
            try:
                print(f"  正在爬取: {url}")
                soup = self.fetch_and_parse(url)
                notices = self.parse_notice_list(soup, url, section)

                # 过滤旧通知
                recent = []
                for n in notices:
                    if n["date"] != "未知":
                        try:
                            nd = datetime.strptime(n["date"], "%Y-%m-%d")
                            if nd >= cutoff:
                                recent.append(n)
                        except ValueError:
                            pass
                    else:
                        # 日期未知的也保留（可能是格式变化）
                        recent.append(n)

                print(f"    找到 {len(notices)} 条，{len(recent)} 条在时间范围内")
                all_notices.extend(recent)

            except Exception as e:
                print(f"  [ERROR] 爬取 {self.name} - {url} 失败: {e}")

        return all_notices

    @staticmethod
    def _parse_date(text):
        """从文本中提取日期（支持多种格式）"""
        if not text:
            return None
        text = text.strip()
        # 2026-05-11 或 2026/04/30
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
        if m:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        # 05-11 或 04/30（当年）
        m = re.search(r"(\d{1,2})[-/](\d{1,2})", text)
        if m:
            return datetime(datetime.now().year, int(m.group(1)), int(m.group(2)))
        # 2024年12月15日
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
        if m:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return None
