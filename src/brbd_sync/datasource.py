from textwrap import indent
from typing import Any, Callable

import click
from pydantic import BaseModel


class Subscriber(BaseModel):
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


class InvalidMailingListException(click.ClickException):
    def __init__(self, description: str, dupe_emails: dict[str, list[Subscriber]]):
        def pretty_dupe(email: str, subs: list[Subscriber]) -> str:
            pretty_subs = "\n".join([str(sub) for sub in subs])
            return f"{email}\n{indent(pretty_subs, ' ' * 4)}"

        pretty_dupes = "\n".join(
            pretty_dupe(email, subs) for email, subs in dupe_emails.items()
        )
        super().__init__(
            f"""\
Invalid data in {description}.

Duplicate emails:

{indent(pretty_dupes, " " * 4)}
"""
        )


class MailingListDatasource(BaseModel):
    description: str
    subscribers: list[Subscriber]

    def model_post_init(self, context: Any):
        self._subscriber_by_email: dict[str, Subscriber] = {}

        subscribers_by_email = group_by(self.subscribers, lambda s: s.email)
        dupe_emails: dict[str, list[Subscriber]] = {}
        for email, subscribers in subscribers_by_email.items():
            assert email is not None, f"Unexpected None email: {subscribers}"

            match len(subscribers):
                case 0:
                    assert False
                case 1:
                    (subscriber,) = subscribers
                    self.subscribers.append(subscriber)
                    self._subscriber_by_email[email] = subscriber
                case _:
                    dupe_emails[email] = subscribers

        if len(dupe_emails) > 0:
            raise InvalidMailingListException(self.description, dupe_emails)

    def get_subscriber(self, *, email: str) -> Subscriber:
        return self._subscriber_by_email[email]
