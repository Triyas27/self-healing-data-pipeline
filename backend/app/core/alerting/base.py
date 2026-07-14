from dataclasses import dataclass


@dataclass
class AlertPayload:
    run_id: int
    quarantined_count: int
    error_types: dict[str, int]


class Alerter:
    def send(self, payload: AlertPayload) -> None:
        raise NotImplementedError
