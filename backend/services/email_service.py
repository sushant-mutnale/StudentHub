"""
Email Service

Handles sending emails via SMTP for OTP verification, password reset, etc.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.sender_email = settings.sender_email
        self.sender_password = settings.sender_password
        self.email_from = settings.email_from or settings.sender_email
    
    def _is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(self.sender_email and self.sender_password)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        Returns True if successful, False otherwise.
        """
        if not self._is_configured():
            logger.warning("Email not configured. Skipping email send.")
            # In development, log the email content
            logger.info(f"[DEV] Would send email to {to_email}: {subject}")
            logger.info(f"[DEV] Content: {text_content or html_content[:200]}")
            return True  # Return True in dev mode so flow continues
        
        try:
        try:
            # Prepare message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = to_email
            
            # Attach text and HTML parts
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Define synchronous sending function
            def _send_sync():
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    # Timeout after 10s to prevent hanging
                    server.timeout = 10
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.email_from, to_email, msg.as_string())

            # Run in threadpool to avoid blocking async event loop
            from fastapi.concurrency import run_in_threadpool
            await run_in_threadpool(_send_sync)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_otp_email(self, to_email: str, otp_code: str, purpose: str = "verification") -> bool:
        """Send OTP verification email."""
        
        subject_map = {
            "verification": "Verify Your Email - StudentHub",
            "password_reset": "Password Reset - StudentHub",
            "signup": "Complete Your Registration - StudentHub"
        }
        
        subject = subject_map.get(purpose, "Your OTP Code - StudentHub")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7fa; margin: 0; padding: 20px; }}
                .container {{ max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 40px 20px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 28px; }}
                .content {{ padding: 40px 30px; text-align: center; }}
                .otp-box {{ background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 2px dashed #6366f1; border-radius: 12px; padding: 20px; margin: 30px 0; }}
                .otp-code {{ font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #6366f1; font-family: 'Courier New', monospace; }}
                .message {{ color: #64748b; font-size: 16px; line-height: 1.6; }}
                .warning {{ color: #ef4444; font-size: 14px; margin-top: 20px; }}
                .footer {{ background: #f8fafc; padding: 20px; text-align: center; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 StudentHub</h1>
                </div>
                <div class="content">
                    <p class="message">
                        {"Please verify your email to complete registration." if purpose == "signup" else 
                         "Use this code to reset your password." if purpose == "password_reset" else
                         "Here's your verification code."}
                    </p>
                    <div class="otp-box">
                        <div class="otp-code">{otp_code}</div>
                    </div>
                    <p class="message">This code expires in <strong>10 minutes</strong>.</p>
                    <p class="warning">⚠️ Don't share this code with anyone.</p>
                </div>
                <div class="footer">
                    © 2026 StudentHub. All rights reserved.
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        StudentHub - {subject}
        
        Your OTP Code: {otp_code}
        
        This code expires in 10 minutes.
        Don't share this code with anyone.
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
