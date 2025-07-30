from typing import Any
from urllib.parse import urlparse

import requests
from pydantic import BaseModel


class SkippableEmailError(Exception):
    def __init__(self, operation: str, code: str, detail: str):
        self.operation = operation
        self.code = code
        self.detail = detail


class Subscriber(BaseModel):
    type: str
    email_address: str
    tags: set[str]
    metadata: dict[str, str]


class ListSubscribersResponse(BaseModel):
    results: list[Subscriber]
    next: str | None


BUTTONDOWN_API_DOMAIN = "api.buttondown.com"


class Client:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def get(self, path: str) -> Any:  # pragma: no cover (requires internet)
        return self._call("GET", path, None).json()

    def post(self, path: str, data: Any) -> Any:  # pragma: no cover (requires internet)
        return self._call("POST", path, data).json()

    def delete(self, path: str):  # pragma: no cover (requires internet)
        self._call("DELETE", path, None)

    def patch(
        self, path: str, data: Any
    ) -> Any:  # pragma: no cover (requires internet)
        return self._call("PATCH", path, data).json()

    def _call(
        self, method: str, path: str, data: Any | None
    ) -> requests.Response:  # pragma: no cover (requires internet)
        path = path.removeprefix("/")

        response = requests.request(
            method,
            f"https://{BUTTONDOWN_API_DOMAIN}/{path}",
            headers={"Authorization": f"Token {self._api_key}"},
            json=data,
        )
        response.raise_for_status()

        return response

    def list_subscribers(
        self,
    ) -> list[Subscriber]:  # pragma: no cover (requires internet)
        next = "/v1/subscribers"

        subscribers: list[Subscriber] = []

        while next is not None:
            response = self.get(next)

            parsed_response = ListSubscribersResponse(**response)
            subscribers.extend(parsed_response.results)

            if parsed_response.next is None:
                next = None
            else:
                next_url = urlparse(parsed_response.next)
                assert next_url.netloc == BUTTONDOWN_API_DOMAIN
                assert isinstance(next_url.path, str)
                assert isinstance(next_url.query, str)
                next = next_url.path + "?" + next_url.query

        return subscribers


class Operation(BaseModel):
    def doit(self, api_client: Client):
        raise NotImplementedError()  # pragma: no cover (duh)


class AddSub(Operation):
    email: str
    tags: set
    metadata: dict[str, str]

    def doit(self, api_client: Client):  # pragma: no cover (requires internet)
        sub = Subscriber(
            email_address=self.email,
            type="regular",
            tags=self.tags,
            metadata=self.metadata,
        )
        try:
            api_client.post("/v1/subscribers", data=sub.model_dump(mode="json"))
        except requests.HTTPError as e:
            json = e.response.json()
            code = json.get("code")
            if e.response.status_code == 400 and code == "subscriber_blocked":
                raise SkippableEmailError(
                    operation="add",
                    code=code,
                    detail=json.get("detail"),
                )
            raise


class EditSub(Operation):
    old_email: str
    new_email: str | None = None
    tags: set | None = None
    metadata: dict[str, str] | None = None

    def is_noop(self) -> bool:
        return self.new_email is None and self.tags is None and self.metadata is None

    def doit(self, api_client: Client):  # pragma: no cover (requires internet)
        data = {}
        if self.new_email is not None:
            data["email_address"] = self.new_email

        if self.tags is not None:
            data["tags"] = list(self.tags)

        if self.metadata is not None:
            data["metadata"] = self.metadata

        try:
            return api_client.patch(f"/v1/subscribers/{self.old_email}", data=data)
        except requests.HTTPError as e:
            json = e.response.json()
            code = json.get("code")
            if e.response.status_code == 400 and code == "email_invalid":
                raise SkippableEmailError(
                    operation="edit",
                    code=code,
                    detail=json.get("detail"),
                )
            raise


class DeleteSub(Operation):
    email: str

    def doit(self, api_client: Client):  # pragma: no cover (requires internet)
        return api_client.delete(f"/v1/subscribers/{self.email}")
