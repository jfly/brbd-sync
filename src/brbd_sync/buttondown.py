import requests
from pydantic import BaseModel, Field

from .datasource import MailingListDatasource, Subscriber


class BaserowSubscriber(Subscriber):
    email: str | None = Field(alias="email_address")


class BaserowListSubscribersResponse(BaseModel):
    results: list[BaserowSubscriber]
    next: str | None


def load_subscribers(api_key: str) -> MailingListDatasource:
    next = "https://api.buttondown.com/v1/subscribers"
    headers = {"Authorization": f"Token {api_key}"}

    subscribers: list[Subscriber] = []

    while next is not None:
        response = requests.request("GET", next, headers=headers)
        assert response.status_code == 200
        parsed_response = BaserowListSubscribersResponse(**response.json())
        subscribers.extend(parsed_response.results)

        next = parsed_response.next

    return MailingListDatasource(subscribers=subscribers)
