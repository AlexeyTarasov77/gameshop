from email.message import EmailMessage
from pydantic import validate_email

import aiosmtplib


class AsyncMailer:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        default_sender: str | None = None,
    ) -> None:
        self._smtp = aiosmtplib.SMTP(hostname=host, port=port, username=username, password=password)
        self._default_sender = default_sender

    async def send_mail(self, subject: str, body: str, to: str, from_: str | None = None) -> None:
        print("Checking from and default sender")
        if from_ is None and self._default_sender is None:
            raise ValueError("If default_sender is None - from_ is required")
        from_email = from_ or self._default_sender
        print("validating emails")
        validate_email(to)
        validate_email(from_email)
        print("constructing msg")
        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        print("constructed msg. Connecting smtp", message)
        async with self._smtp as smtp:
            print("Connected. Sending message")
            await smtp.send_message(message)
            print("Message sent. Closing conn")
