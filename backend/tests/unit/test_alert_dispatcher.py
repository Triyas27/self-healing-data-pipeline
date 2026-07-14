import logging

from app.config import settings
from app.core.alerting import dispatcher
from app.core.alerting.base import AlertPayload


def test_dispatcher_always_logs_and_skips_unconfigured_channels(monkeypatch, caplog):
    monkeypatch.setattr(settings, "alert_slack_webhook_url", None)
    monkeypatch.setattr(settings, "alert_email_smtp_host", None)

    caplog.set_level(logging.WARNING, logger="pipeline.alerts")
    dispatcher.send_quarantine_alert(AlertPayload(run_id=1, quarantined_count=1, error_types={"invalid_amount": 1}))
    assert "quarantined" in caplog.text.lower()


def test_dispatcher_calls_slack_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "alert_slack_webhook_url", "https://hooks.slack.example/xyz")
    monkeypatch.setattr(settings, "alert_email_smtp_host", None)

    called = {}

    class FakeSlackAlerter:
        def __init__(self, webhook_url):
            called["webhook_url"] = webhook_url

        def send(self, payload):
            called["sent"] = True

    monkeypatch.setattr(dispatcher, "SlackAlerter", FakeSlackAlerter)
    dispatcher.send_quarantine_alert(AlertPayload(run_id=1, quarantined_count=1, error_types={}))
    assert called["webhook_url"] == "https://hooks.slack.example/xyz"
    assert called["sent"] is True


def test_dispatcher_swallows_slack_failure(monkeypatch):
    monkeypatch.setattr(settings, "alert_slack_webhook_url", "https://hooks.slack.example/xyz")
    monkeypatch.setattr(settings, "alert_email_smtp_host", None)

    class BrokenSlackAlerter:
        def __init__(self, webhook_url):
            pass

        def send(self, payload):
            raise RuntimeError("network down")

    monkeypatch.setattr(dispatcher, "SlackAlerter", BrokenSlackAlerter)
    # Must not raise -- a broken optional channel never blocks the guaranteed log alert.
    dispatcher.send_quarantine_alert(AlertPayload(run_id=1, quarantined_count=1, error_types={}))


def test_dispatcher_calls_email_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "alert_slack_webhook_url", None)
    monkeypatch.setattr(settings, "alert_email_smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "alert_email_to", "ops@example.com")

    called = {}

    class FakeEmailAlerter:
        def __init__(self, host, port, from_addr, to_addr):
            called["host"] = host

        def send(self, payload):
            called["sent"] = True

    monkeypatch.setattr(dispatcher, "EmailAlerter", FakeEmailAlerter)
    dispatcher.send_quarantine_alert(AlertPayload(run_id=1, quarantined_count=1, error_types={}))
    assert called["host"] == "smtp.example.com"
    assert called["sent"] is True
