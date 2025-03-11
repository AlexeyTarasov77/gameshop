from typing import NamedTuple


class MailingTemplate(NamedTuple):
    html: str
    text: str


type EmailBody = MailingTemplate | str
