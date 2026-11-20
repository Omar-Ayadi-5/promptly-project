import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content


class SendGridAdapter:
    def send_verification_email(self, to_email, code):
        message = Mail(
            from_email=Email(os.environ['SENDGRID_FROM_EMAIL']),
            to_emails=To(to_email),
            subject='Your Promptly Verification Code',
            plain_text_content=Content("text/plain", f'Your Promptly verification code is: {code}'),
            html_content=Content("text/html", f"<strong>Your Promptly verification code is: {code}</strong>"),
        )
        try:
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            response = sg.send(message)
            return response.status_code
        except Exception as e:
            print(f"Error sending email: {e}")
            return None
