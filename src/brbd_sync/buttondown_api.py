from typing import Any

import requests
from pydantic import BaseModel


class Subscriber(BaseModel):
    email_address: str
    tags: set[str]
    metadata: dict[str, str]


class ListSubscribersResponse(BaseModel):
    results: list[Subscriber]
    next: str | None


class Client:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def get(self, path: str) -> Any:  # pragma: no cover (requires internet)
        path = path.removeprefix("/")

        response = requests.request(
            "GET",
            f"https://api.buttondown.com/{path}",
            headers={"Authorization": f"Token {self._api_key}"},
        )
        assert response.status_code == 200
        return response.json()

    def list_subscribers(
        self,
    ) -> list[Subscriber]:  # pragma: no cover (requires internet)
        next = "/v1/subscribers"

        subscribers: list[Subscriber] = []

        while next is not None:
            response = self.get(next)

            parsed_response = ListSubscribersResponse(**response)
            subscribers.extend(parsed_response.results)

            next = parsed_response.next

        return subscribers


class Operation(BaseModel):
    def doit(self, api_client: Client):
        raise NotImplementedError()  # pragma: no cover (duh)


class AddSub(Operation):
    email: str
    tags: set
    metadata: dict[str, str]

    def doit(self, api_client: Client):  # pragma: no cover (requires internet)
        assert False  # <<<


class EditSub(Operation):
    old_email: str
    new_email: str | None = None
    tags: set | None = None
    metadata: dict[str, str] | None = None

    def is_noop(self) -> bool:
        return self.new_email is None and self.tags is None and self.metadata is None

    def doit(self, api_client: Client):  # pragma: no cover (requires internet)
        assert False  # <<<


class DeleteSub(Operation):
    email: str

    def doit(self, api_client: Client):  # pragma: no cover (requires internet)
        assert False  # <<<
