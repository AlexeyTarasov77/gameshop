from email.message import EmailMessage

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
        self.smtp = aiosmtplib.SMTP(hostname=host, port=port, username=username, password=password)
        self.default_sender = default_sender

    async def send_mail(self, subject: str, body: str, to: str, from_: str | None = None) -> None:
        if from_ is None and self.default_sender is None:
            raise ValueError("If default_sender is None - from_ is required")
        message = EmailMessage()
        message["From"] = from_ or self.default_sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        async with self.smtp as smtp:
            await smtp.send_message(message)
