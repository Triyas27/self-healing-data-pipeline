import logging

from app.core.alerting.base import AlertPayload
from app.core.alerting.email_alert import EmailAlerter
from app.core.alerting.log_alert import LogAlerter
from app.core.alerting.slack_alert import SlackAlerter


def test_log_alerter_logs_warning(caplog):
    caplog.set_level(logging.WARNING, logger="pipeline.alerts")
    LogAlerter().send(
        AlertPayload(run_id=1, quarantined_count=3, error_types={"invalid_amount": 2, "invalid_foreign_key": 1})
    )
    assert "quarantined" in caplog.text.lower()
    assert "3" in caplog.text


def test_slack_alerter_posts_to_webhook(monkeypatch):
    calls = {}

    def fake_post(url, json, timeout):
        calls["url"] = url
        calls["json"] = json

    monkeypatch.setattr("app.core.alerting.slack_alert.httpx.post", fake_post)
    SlackAlerter("https://hooks.slack.example/xyz").send(
        AlertPayload(run_id=1, quarantined_count=2, error_types={"invalid_amount": 2})
    )
    assert calls["url"] == "https://hooks.slack.example/xyz"
    assert "2" in calls["json"]["text"]


def test_email_alerter_sends_via_smtp(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, msg):
            sent["subject"] = msg["Subject"]

    monkeypatch.setattr("app.core.alerting.email_alert.smtplib.SMTP", FakeSMTP)
    EmailAlerter("smtp.example.com", 587, "pipeline@example.com", "ops@example.com").send(
        AlertPayload(run_id=7, quarantined_count=1, error_types={"invalid_amount": 1})
    )
    assert sent["host"] == "smtp.example.com"
    assert "7" in sent["subject"]
