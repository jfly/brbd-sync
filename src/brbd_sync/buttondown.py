import uuid
from typing import Any, Self

import requests
from pydantic import BaseModel, Field

from .util import group_by, unique_group_by


class Subscriber(BaseModel):
    id: str
    email: str = Field(alias="email_address")
    tags: set[str]
    metadata: dict[str, str]

    def model_post_init(self, context: Any):
        self.id = self.metadata.get("id", f"bogus-{uuid.uuid4()}")


class ListSubscribersResponse(BaseModel):
    results: list[Subscriber]
    next: str | None


class Operation(BaseModel):
    pass


class AddSub(Operation):
    email: str
    tags: set
    metadata: dict[str, str]


class EditSub(Operation):
    old_email: str
    new_email: str | None = None
    tags: set | None = None
    metadata: dict[str, str] | None = None

    def is_noop(self) -> bool:
        return self.new_email is None and self.tags is None and self.metadata is None


class DeleteSub(Operation):
    email: str


class Data:
    def __init__(self, subscribers: list[Subscriber]):
        self._subscriber_by_email: dict[str, Subscriber] = unique_group_by(
            subscribers, lambda s: s.email
        )
        self._recompute_indices()

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

    def add(self, op: AddSub, dry_run: bool):
        if not dry_run:
            assert False  # <<<

        id = op.metadata["id"]
        self._add_subscriber(
            Subscriber(
                id=id,
                email_address=op.email,
                tags=op.tags,
                metadata=op.metadata,
            )
        )

    def delete(self, op: DeleteSub, dry_run: bool):
        if not dry_run:
            assert False  # <<<

        self._delete_subscriber(op.email)

    def edit(
        self,
        op: EditSub,
        dry_run: bool,
    ):
        if not dry_run:
            assert False  # <<<

        old_sub = self.get_subscriber(email=op.old_email)
        assert old_sub is not None

        self._delete_subscriber(old_sub.email)
        self._add_subscriber(
            Subscriber(
                id=old_sub.id if op.metadata is None else op.metadata["id"],
                email_address=old_sub.email if op.new_email is None else op.new_email,
                tags=old_sub.tags if op.tags is None else op.tags,
                metadata=old_sub.metadata if op.metadata is None else op.metadata,
            )
        )

    @classmethod
    def load(cls, api_key: str) -> Self:  # pragma: no cover (requires internet)
        next = "https://api.buttondown.com/v1/subscribers"
        headers = {"Authorization": f"Token {api_key}"}

        subscribers: list[Subscriber] = []

        while next is not None:
            response = requests.request("GET", next, headers=headers)
            assert response.status_code == 200
            parsed_response = ListSubscribersResponse(**response.json())
            subscribers.extend(parsed_response.results)

            next = parsed_response.next

        return cls(subscribers=subscribers)
