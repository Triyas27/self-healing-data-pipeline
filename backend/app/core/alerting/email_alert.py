import smtplib
from email.message import EmailMessage

from app.core.alerting.base import AlertPayload, Alerter


class EmailAlerter(Alerter):
    def __init__(self, smtp_host: str, smtp_port: int, from_addr: str, to_addr: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addr = to_addr

    def send(self, payload: AlertPayload) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"Pipeline run {payload.run_id}: {payload.quarantined_count} row(s) quarantined"
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg.set_content(f"Error types: {payload.error_types}")

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5.0) as smtp:
            smtp.send_message(msg)
