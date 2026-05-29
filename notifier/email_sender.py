import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件通知"""

    def __init__(self, email_config):
        self.cfg = email_config
        self.enabled = email_config.get("enabled", False)

    def send(self, notices):
        """发送新通知邮件"""
        if not self.enabled or not notices:
            return False
        try:
            # 按来源分组：学院在前，学校在后
            grouped = self._group_notices(notices)
            content = self._build_html(grouped)
            summary = self._build_summary(grouped)
            subject = f"[校园通知] {summary}"

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.cfg["sender_email"]
            msg["To"] = ", ".join(self.cfg["recipients"])
            msg.attach(MIMEText(content, "html", "utf-8"))

            server = smtplib.SMTP_SSL(self.cfg["smtp_server"], self.cfg["smtp_port"])
            server.login(self.cfg["sender_email"], self.cfg["sender_password"])
            server.send_message(msg)
            server.quit()
            logger.info(f"[OK] 邮件已发送，共 {len(notices)} 条通知")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 邮件发送失败: {e}")
            return False

    def send_no_new(self):
        """发送"暂无新通知"提示邮件"""
        if not self.enabled:
            return False
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            subject = f"[校园通知] {now} 暂无新通知"

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.cfg["sender_email"]
            msg["To"] = ", ".join(self.cfg["recipients"])
            msg.attach(MIMEText(self._build_empty_html(now), "html", "utf-8"))

            server = smtplib.SMTP_SSL(self.cfg["smtp_server"], self.cfg["smtp_port"])
            server.login(self.cfg["sender_email"], self.cfg["sender_password"])
            server.send_message(msg)
            server.quit()
            logger.info("[OK] 暂无新通知邮件已发送")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 邮件发送失败: {e}")
            return False

    def _group_notices(self, notices):
        """将通知按来源分组，学院在前"""
        groups = {}
        for n in notices:
            source = n["source"]
            if source not in groups:
                groups[source] = []
            groups[source].append(n)
        # 排序：微电子学院 → 学工部 → 团委 → 教务处 → 合工大主站
        priority = ["微电子学院", "学工部", "团委", "教务处", "合工大主站"]
        ordered = []
        for key in priority:
            if key in groups:
                ordered.append((key, groups[key]))
                del groups[key]
        for key in sorted(groups.keys()):
            ordered.append((key, groups[key]))
        return ordered

    def _build_summary(self, grouped):
        """生成摘要文字：如 '微电子5条, 教务处2条'"""
        parts = [f"{name}{len(items)}条" for name, items in grouped]
        return "、".join(parts)

    def _build_html(self, grouped):
        """构建分块 HTML 邮件内容"""
        total = sum(len(items) for _, items in grouped)
        summary_rows = ""
        for name, items in grouped:
            sections = {}
            for n in items:
                sec = n.get("section", "")
                sections.setdefault(sec, []).append(n)
            sec_text = "、".join(f"{s}{len(v)}条" for s, v in sections.items())
            summary_rows += f"""
                <tr>
                    <td style="padding:8px 16px;border-bottom:1px solid #f0f0f0">
                        <span style="font-weight:600;color:#333">{name}</span>
                        <span style="color:#999;font-size:13px;float:right">{sec_text}</span>
                    </td>
                </tr>"""

        detail_rows = ""
        for name, items in grouped:
            detail_rows += f"""
            <tr>
                <td style="padding:16px 16px 8px;background:#f7f8fa;font-weight:600;color:#555">
                    {name}（{len(items)}条）
                </td>
            </tr>"""
            for n in items:
                detail_rows += f"""
            <tr>
                <td style="padding:10px 16px;border-bottom:1px solid #eee">
                    <span style="color:#aaa;font-size:11px">[{n.get('section', '')}]</span>
                    <a href="{n['url']}" style="color:#1890ff;text-decoration:none;font-size:14px;margin-left:4px">
                        {n['title']}
                    </a>
                    <span style="color:#999;font-size:12px;float:right">{n['date']}</span>
                </td>
            </tr>"""

        return f"""
        <div style="max-width:700px;margin:20px auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:24px;
                        border-radius:12px 12px 0 0">
                <h2 style="margin:0">校园通知速递</h2>
                <p style="margin:8px 0 0;opacity:0.85">发现 {total} 条新通知</p>
            </div>
            <table style="width:100%;border-collapse:collapse;background:#fff"
                   cellpadding="0" cellspacing="0">
                {summary_rows}
            </table>
            <div style="height:8px;background:#f0f2f5"></div>
            <table style="width:100%;border-collapse:collapse;background:#fff;
                          border-radius:0 0 12px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08)"
                   cellpadding="0" cellspacing="0">
                {detail_rows}
            </table>
            <p style="color:#aaa;font-size:12px;text-align:center;margin-top:16px">
                由 校园通知爬虫 自动推送 | 如需调整请修改 config.yaml
            </p>
        </div>"""

    def _build_empty_html(self, now):
        """构建"暂无新通知"的 HTML 邮件"""
        return f"""
        <div style="max-width:700px;margin:20px auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:24px;
                        border-radius:12px 12px 0 0">
                <h2 style="margin:0">校园通知速递</h2>
                <p style="margin:8px 0 0;opacity:0.85">{now} 检查完成</p>
            </div>
            <div style="background:#fff;padding:40px 24px;text-align:center;
                        border-radius:0 0 12px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
                <p style="font-size:18px;color:#666;margin:0">暂无新通知</p>
                <p style="font-size:13px;color:#aaa;margin:12px 0 0">爬虫正常运行中，有新通知会立即推送</p>
            </div>
            <p style="color:#aaa;font-size:12px;text-align:center;margin-top:16px">
                由 校园通知爬虫 自动推送 | 如需调整请修改 config.yaml
            </p>
        </div>"""

