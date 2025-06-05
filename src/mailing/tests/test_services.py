from contextlib import nullcontext as does_not_raise
from email.message import EmailMessage
from core.logging import stub_logger
from unittest.mock import create_autospec

import pytest
from faker import Faker

from mailing.domain.services import MailingService

fake = Faker()


@pytest.fixture
def service() -> MailingService:
    mailer = MailingService(
        stub_logger, fake.domain_name(), 2525, fake.user_name(), fake.password()
    )
    mock_smtp = create_autospec(mailer._smtp, instance=True)
    mock_smtp.__aenter__ = type(mailer._smtp).__aenter__
    mock_smtp.__aexit__ = type(mailer._smtp).__aexit__
    mailer._smtp = mock_smtp
    return mailer


class TestMailingService:
    @pytest.mark.parametrize(
        ["subject", "body", "to", "from_", "default_sender", "expected"],
        [
            (
                fake.sentence(3),
                fake.sentence(),
                fake.email(),
                fake.email(),
                None,
                does_not_raise(),
            ),
            (
                fake.sentence(3),
                fake.sentence(),
                fake.email(),
                None,
                None,
                pytest.raises(AssertionError),
            ),
            (
                fake.sentence(3),
                fake.sentence(),
                fake.email(),
                None,
                fake.email(),
                does_not_raise(),
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_send_mail(
        self,
        service,
        subject: str,
        body: str,
        to: str,
        from_: str | None,
        default_sender: str | None,
        expected,
    ):
        service._default_sender = default_sender
        with expected:
            await service.send_mail(subject, body, to, from_)
        if expected is does_not_raise():
            message = EmailMessage()
            message["From"] = from_
            message["To"] = to
            message["Subject"] = subject
            message.set_content(body)
            service._smtp.connect.assert_called_once()
            service._smtp.quit.assert_called_once()
            service._smtp.send_message.assert_called_with(message)
