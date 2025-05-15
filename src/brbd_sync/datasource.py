from typing import Any

from pydantic import BaseModel


class Subscriber(BaseModel):
    email: str | None
    tags: set[str]


class MailingListDatasource(BaseModel):
    subscribers: list[Subscriber]

    def model_post_init(self, context: Any):
        self._subscribers_by_email = {s.email: s for s in self.subscribers}

    def get_subscriber(self, *, email: str) -> Subscriber:
        return self._subscribers_by_email[email]
