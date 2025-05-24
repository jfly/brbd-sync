from typing import Any, Callable, Self

from baserowapi import Baserow
from pydantic import BaseModel, Field


class BaserowSubscriber(BaseModel):
    id: str
    email: str
    tags: set[str]
    metadata: dict[str, str]
    full_name: str = Field(alias="Full Name")

    def model_post_init(self, context: Any):
        self.metadata["id"] = self.id


def group_by[K, V](arr: list[V], key: Callable[[V], K]) -> dict[K, list[V]]:
    result: dict[K, list[V]] = {}
    for v in arr:
        k = key(v)
        if k not in result:
            result[k] = []

        result[k].append(v)

    return result


class BaserowData(BaseModel):
    description: str
    subscribers: list[BaserowSubscriber]

    def model_post_init(self, context: Any):
        self._subscriber_by_id: dict[str, BaserowSubscriber] = {}

        subscribers_by_id = group_by(self.subscribers, lambda s: s.id)
        for id, subscribers in subscribers_by_id.items():
            assert len(subscribers) == 1, (
                f"Unexpectedly found {len(subscribers)} rows with id {id}"
            )
            (subscriber,) = subscribers
            self.subscribers.append(subscriber)
            self._subscriber_by_id[id] = subscriber

    def get_subscriber(self, *, id: str) -> BaserowSubscriber:
        return self._subscriber_by_id[id]

    @classmethod
    def load(
        cls,
        api_key: str,
        table_id: int,
        tags_column_names: list[str],
        metadata_column_names: list[str],
    ) -> Self:
        baserow = Baserow(url="https://api.baserow.io", token=api_key)
        table = baserow.get_table(table_id)

        subscribers: list[BaserowSubscriber] = []
        for row in table.row_generator():
            assert row.id is not None, f"Unexpectedly found a row with a None id? {row}"

            tags = set(
                f"{tags_column_name}: {tag}"
                for tags_column_name in tags_column_names
                for tag in row[tags_column_name]
            )

            metadata = {
                metadata_key: row[metadata_key]
                for metadata_key in metadata_column_names
            }

            joined_emails = row["Email"]

            # Ignore people with no email.
            if joined_emails == "":
                continue

            emails = [email.strip() for email in joined_emails.split(";")]

            for n, email in enumerate(emails):
                unique_id = str(row.id)
                if len(emails) > 1:
                    unique_id += f"-{n + 1}"
                br_sub = BaserowSubscriber(
                    **row.to_dict(),
                    tags=tags,
                    email=email,
                    metadata=metadata,
                    id=unique_id,
                )
                subscribers.append(br_sub)

        return cls(description="Baserow", subscribers=subscribers)
