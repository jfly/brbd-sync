from typing import Any, Callable, Self

from baserowapi import Baserow
from pydantic import BaseModel, Field

from brbd_sync.util import unique_group_by


def assert_not_none[V](v: V | None) -> V:
    assert v is not None
    return v


class Subscriber(BaseModel):
    id: str
    email: str | None
    tags: set[str]
    metadata: dict[str, str]
    full_name: str = Field(alias="Full Name")

    def model_post_init(self, context: Any):
        self.metadata["id"] = self.id
        if self.email == "":
            self.email = None


class SubscriberWithEmail(BaseModel):
    id: str
    email: str
    tags: set[str]
    metadata: dict[str, str]
    full_name: str


def group_by[K, V](arr: list[V], key: Callable[[V], K]) -> dict[K, list[V]]:
    result: dict[K, list[V]] = {}
    for v in arr:
        k = key(v)
        if k not in result:
            result[k] = []

        result[k].append(v)

    return result


class DataWithUniqueEmails(BaseModel):
    subscribers: list[SubscriberWithEmail]

    def model_post_init(self, context: Any):
        self._subscriber_by_id = unique_group_by(self.subscribers, lambda s: s.id)
        self._subscriber_by_email = unique_group_by(self.subscribers, lambda s: s.email)

    def get_subscriber(
        self, *, id: str | None = None, email: str | None = None
    ) -> SubscriberWithEmail | None:
        params = [val for val in [id, email] if val is not None]
        assert len(params) == 1, "Must query on exactly one field"

        if id is not None:
            return self._subscriber_by_id.get(id)
        elif email is not None:
            return self._subscriber_by_email.get(email)
        else:
            assert False, "Must query for something"  # pragma: no cover


class Data(BaseModel):
    subscribers: list[Subscriber]

    def with_no_duplicate_emails(self) -> tuple[list[str], DataWithUniqueEmails]:
        baserow_sub_by_email: dict[str, Subscriber] = {}
        dupe_emails: list[str] = []
        for email, subs in group_by(self.subscribers, lambda s: s.email).items():
            if email is None:
                continue

            match len(subs):
                case 0:
                    assert False, (
                        f"Unexpectedly found no Baserow rows with email {email}"
                    )  # pragma: no cover
                case 1:
                    (sub,) = subs
                case _:
                    dupe_emails.append(email)
                    sub = subs[0]

            baserow_sub_by_email[email] = sub

        return (
            dupe_emails,
            DataWithUniqueEmails(
                subscribers=[
                    SubscriberWithEmail(
                        id=s.id,
                        email=assert_not_none(s.email),
                        tags=s.tags,
                        metadata=s.metadata,
                        full_name=s.full_name,
                    )
                    for s in baserow_sub_by_email.values()
                ]
            ),
        )

    @classmethod
    def load(
        cls,
        api_key: str,
        table_id: int,
        tags_column_names: list[str],
        metadata_column_names: list[str],
    ) -> Self:  # pragma: no cover (requires internet)
        baserow = Baserow(url="https://api.baserow.io", token=api_key)
        table = baserow.get_table(table_id)

        subscribers: list[Subscriber] = []
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
                br_sub = Subscriber(
                    **row.to_dict(),
                    tags=tags,
                    email=email,
                    metadata=metadata,
                    id=unique_id,
                )
                subscribers.append(br_sub)

        return cls(subscribers=subscribers)
