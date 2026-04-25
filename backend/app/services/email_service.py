from __future__ import annotations

import resend

from app.auth.providers.email_otp import EmailDelivery, EmailMessage
from app.core.config import settings


class ResendEmailDelivery(EmailDelivery):
    async def send(self, message: EmailMessage) -> None:
        resend.api_key = settings.RESEND_API_KEY
        await resend.Emails.send_async(
            {
                "from": settings.EMAIL_FROM_ADDRESS,
                "to": [message.to_email],
                "subject": message.subject,
                "text": message.body,
            }
        )
