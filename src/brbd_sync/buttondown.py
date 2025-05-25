import uuid
from typing import Self

from pydantic import BaseModel

from . import buttondown_api as api
from .util import group_by, unique_group_by


class Subscriber(BaseModel):
    id: str
    email: str
    tags: set[str]
    metadata: dict[str, str]


class Data:
    def __init__(self, subscribers: list[Subscriber], api_client: api.Client):
        self._subscriber_by_email: dict[str, Subscriber] = unique_group_by(
            subscribers, lambda s: s.email
        )
        self._recompute_indices()
        self._api_client = api_client

    @property
    def subscribers(self) -> list[Subscriber]:
        return list(self._subscriber_by_email.values())

    def _add_subscriber(self, new_sub: Subscriber):
        assert new_sub.email not in self._subscriber_by_email, (
            f"Email {new_sub.email} already exists."
        )
        self._subscriber_by_email[new_sub.email] = new_sub
        self._recompute_indices()

    def _delete_subscriber(self, email: str):
        del self._subscriber_by_email[email]
        self._recompute_indices()

    def _recompute_indices(self):
        self._subscribers_by_id: dict[str, list[Subscriber]] = group_by(
            self.subscribers, lambda s: s.id
        )

    def get_subscribers(self, *, id: str) -> list[Subscriber]:
        return self._subscribers_by_id.get(id, [])

    def get_subscriber(self, *, email: str) -> Subscriber | None:
        return self._subscriber_by_email.get(email)

    def add(self, op: api.AddSub, dry_run: bool):
        if not dry_run:
            op.doit(self._api_client)

        id = op.metadata["id"]
        self._add_subscriber(
            Subscriber(
                id=id,
                email=op.email,
                tags=op.tags,
                metadata=op.metadata,
            )
        )

    def delete(self, op: api.DeleteSub, dry_run: bool):
        if not dry_run:
            op.doit(self._api_client)

        self._delete_subscriber(op.email)

    def edit(self, op: api.EditSub, dry_run: bool):
        if not dry_run:
            op.doit(self._api_client)

        old_sub = self.get_subscriber(email=op.old_email)
        assert old_sub is not None

        self._delete_subscriber(old_sub.email)
        self._add_subscriber(
            Subscriber(
                id=old_sub.id if op.metadata is None else op.metadata["id"],
                email=old_sub.email if op.new_email is None else op.new_email,
                tags=old_sub.tags if op.tags is None else op.tags,
                metadata=old_sub.metadata if op.metadata is None else op.metadata,
            )
        )

    @classmethod
    def load(
        cls, api_client: api.Client
    ) -> Self:  # pragma: no cover (requires internet)
        subscribers: list[Subscriber] = []
        for api_sub in api_client.list_subscribers():
            subscribers.append(
                Subscriber(
                    id=api_sub.metadata.get("id", f"bogus-{uuid.uuid4()}"),
                    email=api_sub.email_address,
                    tags=api_sub.tags,
                    metadata=api_sub.metadata,
                )
            )

        return cls(subscribers=subscribers, api_client=api_client)
