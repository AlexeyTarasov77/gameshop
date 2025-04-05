from uuid import UUID
from mailing.domain.interfaces import MailingTemplate
from mailing.templates.template_parser import parse


class EmailTemplates:
    async def signup(self, username: str, link: str):
        text = (
            f"Здравствуйте, {username}. Ваш аккаунт был успешно создан."
            "Для активации аккаунта перейдите по ссылке ниже и подтверждите активацию аккаунта:"
            f"\t{link}\t"
        )
        html = await parse("signup.html", username=username, link=link)
        return MailingTemplate(html, text)

    async def reset_password(self, username: str, link: str):
        text = (
            f"Дорогой {username}, мы получили запрос на сброс пароля вашего аккаунта."
            f"\nДля обновления пароля следуйте ссылке ниже:"
            f"\n{link}"
            "\nЕсли это были не вы - игнорируйте это письмо"
        )
        html = await parse("reset_password.html", username=username, link=link)
        return MailingTemplate(html, text)

    async def new_activation_token(self, username: str, token: str, link: str):
        text = (
            f"Здраствуйте, {username}!\n"
            f"Новый токен для активации аккаунта: {token}\n"
            "Перейдите по ссылке ниже для активации аккаунта\n"
            f"\t{link}\t"
        )
        html = await parse(
            "new_activation_token.html", username=username, token=token, link=link
        )
        return MailingTemplate(html, text)

    async def email_change(self, username: str, link: str):
        text = (
            f"Здраствуйте, {username}!\n"
            "Мы получили запрос на смену email'a\n"
            "Для того что бы подтвердить смену email'a, перейдите по ссылке ниже:\n"
            f"\t{link}\n"
            "Если это были не вы - игнорируйте это сообщение"
        )
        html = await parse("email_change.html", username=username, link=link)
        return MailingTemplate(html, text)

    async def order_checkout(self, order_details_link: str, order_id: UUID):
        text = (
            "Здраствуйте, дорогой покупатель!\n"
            "Ваш заказ был успешно оформлен и принят в обработку.\n"
            f"Уникальный номер вашего заказа: {order_id}\n"
            "Для просмотра деталей заказа и отслеживания его статуса - перейдите по ссылке ниже\n"
            f"\t{order_details_link}\t"
        )
        html = await parse(
            "order_checkout.html",
            order_id=order_id,
            order_details_link=order_details_link,
        )
        return MailingTemplate(html, text)
