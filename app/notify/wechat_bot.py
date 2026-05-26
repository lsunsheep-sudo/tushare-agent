import json
import logging
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class WeChatBot:
    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    @property
    def enabled(self) -> bool:
        return bool(self._webhook_url)

    def send_markdown(self, content: str) -> bool:
        """通过企微 Webhook 发送 Markdown 消息"""
        if not self.enabled:
            logger.warning("企微 Webhook 未配置，跳过推送")
            return False

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        try:
            req = Request(
                self._webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=5)
            logger.info("企微消息已推送")
            return True
        except Exception as e:
            logger.error(f"企微推送失败: {e}")
            return False

    def send_text(self, content: str, mentioned_list: list[str] | None = None) -> bool:
        """发送文本消息，可选 @ 指定人"""
        if not self.enabled:
            return False
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list or [],
            },
        }
        try:
            req = Request(
                self._webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=5)
            return True
        except Exception as e:
            logger.error(f"企微推送失败: {e}")
            return False
