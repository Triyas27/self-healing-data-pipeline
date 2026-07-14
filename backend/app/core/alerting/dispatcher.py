import logging

from app.config import settings
from app.core.alerting.base import AlertPayload
from app.core.alerting.email_alert import EmailAlerter
from app.core.alerting.log_alert import LogAlerter
from app.core.alerting.slack_alert import SlackAlerter

logger = logging.getLogger(__name__)


def send_quarantine_alert(payload: AlertPayload) -> None:
    """Always logs. Slack/email are best-effort extras that never break the run."""
    LogAlerter().send(payload)

    if settings.alert_slack_webhook_url:
        try:
            SlackAlerter(settings.alert_slack_webhook_url).send(payload)
        except Exception:
            logger.exception("Slack alert failed for run %s", payload.run_id)

    if settings.alert_email_smtp_host and settings.alert_email_to:
        try:
            EmailAlerter(
                settings.alert_email_smtp_host,
                settings.alert_email_smtp_port or 25,
                settings.alert_email_from or "pipeline@localhost",
                settings.alert_email_to,
            ).send(payload)
        except Exception:
            logger.exception("Email alert failed for run %s", payload.run_id)
