"""
Notification services for failures, schema drift, and summary alerts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List

from ..logging_utils import StructuredLogger


class Notifier(ABC):
    @abstractmethod
    def notify(self, subject: str, body: str) -> None:
        ...


@dataclass
class EmailNotifier(Notifier):
    smtp_client: object
    recipients: List[str]
    logger: StructuredLogger

    def notify(self, subject: str, body: str) -> None:  # pragma: no cover - relies on infra
        message = f"Subject: {subject}\n\n{body}"
        for recipient in self.recipients:
            self.smtp_client.sendmail("bronze@dataplatform", recipient, message)
        self.logger.info("notifier.email.sent", {"subject": subject, "recipients": self.recipients})


@dataclass
class CompositeNotifier(Notifier):
    notifiers: Iterable[Notifier]

    def notify(self, subject: str, body: str) -> None:
        for notifier in self.notifiers:
            notifier.notify(subject, body)


@dataclass
class LoggerNotifier(Notifier):
    logger: StructuredLogger

    def notify(self, subject: str, body: str) -> None:
        self.logger.info("notifier.logger", {"subject": subject, "body": body})
