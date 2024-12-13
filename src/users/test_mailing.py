import asyncio
from contextlib import nullcontext as does_not_raise
from email.message import EmailMessage
from unittest.mock import create_autospec

import pytest
from faker import Faker

from users.mailing import AsyncMailer

fake = Faker()


@pytest.fixture
def mailer() -> AsyncMailer:
    mailer = AsyncMailer("test", 2525, "test", "dsfkjasdhrfsda")
    mock_smtp = create_autospec(mailer._smtp, instance=True)
    mock_smtp.__aenter__ = type(mailer._smtp).__aenter__
    mock_smtp.__aexit__ = type(mailer._smtp).__aexit__
    mailer._smtp = mock_smtp
    return mailer


class TestAsyncMailier:
    @pytest.mark.parametrize(
        ["subject", "body", "to", "from_", "default_sender", "expected"],
        [
            (fake.sentence(3), fake.sentence(), fake.email(), fake.email(), None, does_not_raise()),
            (
                fake.sentence(3),
                fake.sentence(),
                "invalid",
                fake.email(),
                None,
                pytest.raises(ValueError),
            ),
            (
                fake.sentence(3),
                fake.sentence(),
                fake.email(),
                "invalid",
                None,
                pytest.raises(ValueError),
            ),
            (fake.sentence(3), fake.sentence(), fake.email(), None, None, pytest.raises(ValueError)),
            (fake.sentence(3), fake.sentence(), fake.email(), None, fake.email(), does_not_raise()),
        ],
    )
    def test_send_mail(
        self,
        mailer: AsyncMailer,
        subject: str,
        body: str,
        to: str,
        from_: str | None,
        default_sender: str | None,
        expected,
    ):
        mailer._default_sender = default_sender
        with expected:
            asyncio.run(mailer.send_mail(subject, body, to, from_))
        if expected is does_not_raise():
            message = EmailMessage()
            message["From"] = from_
            message["To"] = to
            message["Subject"] = subject
            message.set_content(body)
            mailer._smtp.connect.assert_called_once()
            mailer._smtp.quit.assert_called_once()
            mailer._smtp.send_message.assert_called_with(message)
