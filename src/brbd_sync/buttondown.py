import uuid
from typing import Any, Self

import requests
from pydantic import BaseModel, Field

from .util import group_by, unique_group_by


class ButtondownSubscriber(BaseModel):
    id: str
    email: str = Field(alias="email_address")
    tags: set[str]
    metadata: dict[str, str]

    def model_post_init(self, context: Any):
        self.id = self.metadata.get("id", f"bogus-{uuid.uuid4()}")


class ButtondownListSubscribersResponse(BaseModel):
    results: list[ButtondownSubscriber]
    next: str | None


class ButtondownData(BaseModel):
    description: str
    subscribers: list[ButtondownSubscriber]

    def model_post_init(self, context: Any):
        self._subscribers_by_id: dict[str, list[ButtondownSubscriber]] = group_by(
            self.subscribers, lambda s: s.id
        )
        self._subscriber_by_email: dict[str, ButtondownSubscriber] = unique_group_by(
            self.subscribers, lambda s: s.email
        )

    def get_subscribers(self, *, id: str) -> list[ButtondownSubscriber]:
        return self._subscribers_by_id[id]

    def get_subscriber(self, *, email: str) -> ButtondownSubscriber:
        return self._subscriber_by_email[email]

    @classmethod
    def load(cls, api_key: str) -> Self:
        next = "https://api.buttondown.com/v1/subscribers"
        headers = {"Authorization": f"Token {api_key}"}

        subscribers: list[ButtondownSubscriber] = []

        while next is not None:
            response = requests.request("GET", next, headers=headers)
            assert response.status_code == 200
            parsed_response = ButtondownListSubscribersResponse(**response.json())
            subscribers.extend(parsed_response.results)

            next = parsed_response.next

        return cls(description="Buttondown", subscribers=subscribers)
