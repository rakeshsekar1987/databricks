"""
Notification services for failures, schema drift, and summary alerts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List

import requests

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


@dataclass
class SendGridNotifier(Notifier):
    api_key: str
    sender: str
    recipients: List[str]
    logger: StructuredLogger

    def notify(self, subject: str, body: str) -> None:
        payload = {
            "personalizations": [{"to": [{"email": recipient} for recipient in self.recipients]}],
            "from": {"email": self.sender},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        try:
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            self.logger.info("notifier.sendgrid.sent", {"subject": subject, "recipients": self.recipients})
        except Exception as exc:  # pragma: no cover - network dependent
            self.logger.error("notifier.sendgrid.failed", {"error": str(exc), "subject": subject})
