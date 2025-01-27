import asyncio
from email.message import EmailMessage
from logging import Logger
from pydantic import validate_email

import aiosmtplib


class AsyncMailer:
    def __init__(
        self,
        logger: Logger,
        host: str,
        port: int,
        username: str,
        password: str,
        default_sender: str | None = None,
    ) -> None:
        self._smtp = aiosmtplib.SMTP(
            hostname=host, port=port, username=username, password=password
        )
        self._default_sender = default_sender
        self._logger = logger

    async def _send_mail(
        self, subject: str, body: str, to: str, from_: str | None = None
    ) -> None:
        if from_ is None and self._default_sender is None:
            raise ValueError("If default_sender is None - from_ is required")
        from_email = from_ or self._default_sender
        validate_email(to)
        validate_email(str(from_email))
        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        async with self._smtp as smtp:
            await smtp.send_message(message)

    async def send_mail_with_timeout(
        self,
        subject: str,
        body: str,
        to: str,
        from_: str | None = None,
        *,
        timeout: float = 3,
    ):
        email_details = f"(to={to}, subject={subject})"
        try:
            await asyncio.wait_for(self._send_mail(subject, body, to, from_), timeout)
            self._logger.info("Email was succesfully sent %s", email_details)
        except asyncio.TimeoutError:
            self._logger.warning("Timeout finish to send email %s", email_details)
        except Exception as e:
            self._logger.exception(f"Failed to send email {email_details}", e)
