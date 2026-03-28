import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def send_gmail(to, subject, message_text, html=None):
    creds = Credentials.from_authorized_user_file(
        settings.GMAIL_TOKEN_PATH,
        ["https://www.googleapis.com/auth/gmail.send"],
    )

    service = build("gmail", "v1", credentials=creds)

    message = MIMEMultipart("alternative")

    message["to"] = to
    message["subject"] = subject

    # Plain text
    message.attach(MIMEText(message_text, "plain"))

    # Optional HTML
    if html:
        message.attach(MIMEText(html, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()
