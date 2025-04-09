from logging import Logger
from httpx import AsyncClient

from core.utils.httpx_utils import log_request, log_response


class TelegramClientError(Exception): ...


class TelegramClient:
    def __init__(self, token: str, client: AsyncClient, logger: Logger) -> None:
        self._token = token
        self._client = client
        self._logger = logger
        self._base_url = f"https://api.telegram.org/bot{self._token}"

    async def send_msg(self, chat_id: int, text: str):
        self._logger.info(
            "Sending telegram msg to chat #%s with text:\n%s", chat_id, text
        )
        with log_request("TelegramClient.send_msg", self._logger):
            resp = await self._client.post(
                self._base_url + "/sendMessage", json={"chat_id": chat_id, "text": text}
            )
            log_response(resp, self._logger)
            resp.raise_for_status()
        data = resp.json()
        if not data["ok"]:
            self._logger.error(
                "Failed to send telegram msg to #%s. Description: %s",
                chat_id,
                data["description"],
            )
            raise TelegramClientError(data["description"])
