from uuid import UUID
from mailing.domain.interfaces import MailingTemplate
from mailing.templates.template_parser import parse


class EmailTemplates:
    async def signup(self, username: str, link: str) -> MailingTemplate:
        text = (
            f"Здравствуйте, {username}. Ваш аккаунт был успешно создан."
            "Для активации аккаунта перейдите по ссылке ниже и подтверждите активацию аккаунта:"
            f"\t{link}\t"
        )
        html = await parse("signup.html", username=username, link=link)
        return MailingTemplate(html, text)

    async def reset_password(self, username: str, link: str) -> str:
        return (
            f"Дорогой {username}, мы получили запрос на сброс пароля вашего аккаунта."
            f"\nДля обновления пароля следуйте ссылке ниже:"
            f"\n{link}"
            "\nЕсли это были не вы - игнорируйте это письмо"
        )

    async def new_activation_token(self, token: str, link: str) -> str:
        return (
            f"Новый токен для активации аккаунта: {token}\n"
            "Перейдите по ссылке ниже для активации аккаунта\n"
            f"\t{link}\t"
        )

    async def email_verification(self, link: str) -> str:
        return (
            "Мы получили запрос на смену email'a\n"
            "Для того что бы подтвердить смену email'a, перейдите по ссылке ниже:\n"
            f"\t{link}\n"
            "Если это были не вы - игнорируйте это сообщение"
        )

    async def order_checkout(self, order_details_link: str, order_id: UUID) -> str:
        return (
            "Ваш заказ был успешно оформлен и принят в обработку.\n"
            f"Уникальный номер вашего заказа: {order_id}\n"
            "Для просмотра деталей заказа и отслеживания его статуса - перейдите по ссылке ниже\n"
            f"\t{order_details_link}\t"
        )
