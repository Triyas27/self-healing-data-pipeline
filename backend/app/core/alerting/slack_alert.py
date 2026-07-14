import httpx

from app.core.alerting.base import AlertPayload, Alerter


class SlackAlerter(Alerter):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, payload: AlertPayload) -> None:
        text = (
            f"Run {payload.run_id} quarantined {payload.quarantined_count} row(s). "
            f"Error types: {payload.error_types}"
        )
        httpx.post(self.webhook_url, json={"text": text}, timeout=5.0)
