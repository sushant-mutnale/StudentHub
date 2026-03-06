import base64
import os
import logging
from typing import Optional, List, Tuple


def _send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    attachments: Optional[List[Tuple[str, str, str]]] = None,
):
    """
    attachments: list of tuples (filename, content, mime_type)
    """
    sg_key = os.getenv("SENDGRID_API_KEY")
    from_addr = os.getenv("EMAIL_FROM", "no-reply@studenthub.example.com")

    if sg_key:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

            message = Mail(
                from_email=from_addr, to_emails=to_email, subject=subject, html_content=html
            )
            if attachments:
                for filename, content, mime_type in attachments:
                    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                    attachment = Attachment(
                        FileContent(encoded),
                        FileName(filename),
                        FileType(mime_type),
                        Disposition("attachment"),
                    )
                    message.add_attachment(attachment)
            sg = SendGridAPIClient(sg_key)
            sg.send(message)
            return
        except Exception as e:
            logging.exception("SendGrid send failed, falling back to SMTP: %s", e)

    # SMTP fallback (dev)
    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")

        if attachments:
            for filename, content, mime_type in attachments:
                msg.add_attachment(
                    content.encode("utf-8"),
                    maintype=mime_type.split("/")[0],
                    subtype=mime_type.split("/")[1],
                    filename=filename,
                )

        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        if smtp_host and smtp_user and smtp_pass:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
        else:
            logging.info("Email content (dev): %s", text)
    except Exception:
        logging.exception("SMTP fallback failed while sending email.")


def send_password_reset_email(to_email: str, reset_url: str):
    """Legacy helper kept for backwards compatibility."""
    subject = "StudentHub Password Reset"
    html = f"""
    <p>Hello,</p>
    <p>We received a request to reset your StudentHub password. Click the link below to reset your password. This link expires in 1 hour.</p>
    <p><a href="{reset_url}">Reset your password</a></p>
    <p>If you did not request this, you can safely ignore this email.</p>
    <p>— StudentHub Team</p>
    """
    text = f"Reset your password using this link: {reset_url}"
    _send_email(to_email, subject, html, text)


def send_generic_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    attachments: Optional[List[Tuple[str, str, str]]] = None,
):
    _send_email(to_email, subject, html, text, attachments)
