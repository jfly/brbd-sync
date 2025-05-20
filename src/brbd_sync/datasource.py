from typing import Any, Callable

from pydantic import BaseModel


class Subscriber(BaseModel):
    id: str
    email: str | None
    tags: set[str]
    metadata: dict[str, str]


def group_by[K, V](arr: list[V], key: Callable[[V], K]) -> dict[K, list[V]]:
    result: dict[K, list[V]] = {}
    for v in arr:
        k = key(v)
        if k not in result:
            result[k] = []

        result[k].append(v)

    return result


class MailingListDatasource(BaseModel):
    description: str
    subscribers: list[Subscriber]

    def model_post_init(self, context: Any):
        self._subscriber_by_id: dict[str, Subscriber] = {}

        subscribers_by_id = group_by(self.subscribers, lambda s: s.id)
        for id, subscribers in subscribers_by_id.items():
            assert len(subscribers) == 1, (
                f"Unexpectedly found {len(subscribers)} subs for id {id}"
            )
            (subscriber,) = subscribers
            self.subscribers.append(subscriber)
            self._subscriber_by_id[id] = subscriber

    def get_subscriber(self, *, id: str) -> Subscriber:
        return self._subscriber_by_id[id]
