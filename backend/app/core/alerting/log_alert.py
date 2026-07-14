import logging

from app.core.alerting.base import AlertPayload, Alerter

logger = logging.getLogger("pipeline.alerts")


class LogAlerter(Alerter):
    def send(self, payload: AlertPayload) -> None:
        logger.warning(
            "Run %s produced %d quarantined row(s); error types: %s",
            payload.run_id,
            payload.quarantined_count,
            payload.error_types,
        )
