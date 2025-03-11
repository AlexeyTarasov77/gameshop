import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage
from logging import Logger

import aiosmtplib

from mailing.domain.interfaces import EmailBody


class MailingService:
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

    async def send_mail(
        self,
        subject: str,
        body: EmailBody,
        to: str,
        from_: str | None = None,
        *,
        timeout: float = 5,
    ) -> None:
        from_email = from_ or self._default_sender
        assert from_email, "If default_sender is None - from_ is required"
        if isinstance(body, str):
            message = EmailMessage()
            message.set_content(body)
        else:
            message = MIMEMultipart(
                "alternative",
                _subparts=(MIMEText(body.text, "text"), MIMEText(body.html, "html")),
            )
        message["From"] = from_email
        message["To"] = to
        message["Subject"] = subject
        email_details = f"(to={to}, subject={subject})"
        err_prefix = f"Failed to send email {email_details}"
        async with self._smtp as smtp:
            try:
                await asyncio.wait_for(smtp.send_message(message), timeout)
                self._logger.info("Email was succesfully sent %s", email_details)
            except asyncio.TimeoutError:
                self._logger.warning(f"{err_prefix}. Timeout finished")
            except Exception as e:
                self._logger.exception(f"{err_prefix}. Error: {e}")
