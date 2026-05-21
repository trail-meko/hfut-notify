import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class EmailSender:
    """邮件通知"""

    def __init__(self, email_config):
        self.cfg = email_config
        self.enabled = email_config.get("enabled", False)

    def send(self, notices):
        """发送通知邮件"""
        if not self.enabled or not notices:
            return False
        try:
            # 构建邮件内容
            content = self._build_html(notices)
            subject = f"[校园通知] 发现 {len(notices)} 条新通知"

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.cfg["sender_email"]
            msg["To"] = ", ".join(self.cfg["recipients"])
            msg.attach(MIMEText(content, "html", "utf-8"))

            server = smtplib.SMTP_SSL(self.cfg["smtp_server"], self.cfg["smtp_port"])
            server.login(self.cfg["sender_email"], self.cfg["sender_password"])
            server.send_message(msg)
            server.quit()
            print(f"[OK] 邮件已发送，共 {len(notices)} 条通知")
            return True
        except Exception as e:
            print(f"[ERROR] 邮件发送失败: {e}")
            return False

    def _build_html(self, notices):
        """构建 HTML 邮件内容"""
        rows = ""
        for n in notices:
            rows += f"""
            <tr>
                <td style="padding:12px;border-bottom:1px solid #eee">
                    <span style="color:#888;font-size:12px">【{n['source']}-{n.get('section', '')}】</span><br>
                    <a href="{n['url']}" style="color:#1890ff;text-decoration:none;font-size:15px">
                        {n['title']}
                    </a>
                    <span style="color:#999;font-size:12px;float:right">{n['date']}</span>
                </td>
            </tr>"""

        return f"""
        <div style="max-width:700px;margin:20px auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:24px;
                        border-radius:12px 12px 0 0">
                <h2 style="margin:0">📢 校园通知速递</h2>
                <p style="margin:8px 0 0;opacity:0.85">发现 {len(notices)} 条新通知</p>
            </div>
            <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:0 0 12px 12px;
                          box-shadow:0 2px 8px rgba(0,0,0,0.08)">
                {rows}
            </table>
            <p style="color:#aaa;font-size:12px;text-align:center;margin-top:16px">
                由 校园通知爬虫 自动推送 | 如需调整请修改 config.yaml
            </p>
        </div>"""
