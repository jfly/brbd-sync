import buttondown_api_client
from pydantic import Field

from .datasource import MailingListDatasource, Subscriber


class BaserowSubscriber(Subscriber):
    full_name: str = Field(alias="Full Name")
    email: str | None = Field(alias="Email")


def load_subscribers(api_key: str) -> MailingListDatasource:
    client = buttondown_api_client.AuthenticatedClient(
        base_url="https://api.buttondown.com",
        token=api_key,
    )
    with client as client:
        my_data: MyDataModel = get_my_data_model.sync(client=client)

    api = buttondown_api_client.api

    # <<< baserow = Baserow(url="https://api.baserow.io", token=api_key)
    # <<< table = baserow.get_table(table_id)

    subscribers: list[Subscriber] = []
    # <<< for row in table.row_generator():
    # <<<     br_sub = BaserowSubscriber(**row.to_dict())
    # <<<     subscribers.append(br_sub)

    return MailingListDatasource(subscribers=subscribers)
