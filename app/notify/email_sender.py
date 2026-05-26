import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr

    @property
    def enabled(self) -> bool:
        return bool(self._host and self._user)

    def send(self, to: str, subject: str, html_body: str) -> bool:
        if not self.enabled:
            logger.warning("邮件服务未配置，跳过发送")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.sendmail(self._from, [to], msg.as_string())
            logger.info(f"邮件已发送: {subject}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
