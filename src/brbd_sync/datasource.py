from typing import Any, Callable

from pydantic import BaseModel


class Subscriber(BaseModel):
    email: str | None
    tags: set[str]
    metadata: dict[str, str]


def unique_group_by[K, V](arr: list[V], key: Callable[[V], K]) -> dict[K, V]:
    result = {}
    for v in arr:
        k = key(v)
        assert k not in result, f"Unexpected duplicate key: {k}"
        result[k] = v

    return result


class MailingListDatasource(BaseModel):
    subscribers: list[Subscriber]

    def model_post_init(self, context: Any):
        self._subscribers_by_email = unique_group_by(
            self.subscribers, lambda s: s.email
        )

    def get_subscriber(self, *, email: str) -> Subscriber:
        return self._subscribers_by_email[email]
