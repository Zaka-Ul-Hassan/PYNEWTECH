# backend\app\services\email\email_service.py

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from app.core.load_env import SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT
from app.schemas.email.email_schema import EmailResponseData, SendSystemEmailSchema
from app.schemas.response_schema import ResponseSchema


# Send System Email (Using Predefined SMTP Settings)
def send_system_email(payload: SendSystemEmailSchema) -> ResponseSchema:
    message = MIMEMultipart()
    message["From"] = SMTP_EMAIL
    message["To"] = ", ".join(payload.recipient)
    message["Subject"] = payload.subject
    message.attach(MIMEText(payload.body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, payload.recipient, message.as_string())
        server.quit()

        response_data = EmailResponseData(
            recipient=payload.recipient,
            subject=payload.subject,
            body=payload.body
        )

        return ResponseSchema(
            status=True,
            message="System email sent successfully",
            data=response_data,
        )

    except Exception as ex:
        return ResponseSchema(status=False, message=str(ex), data=None)