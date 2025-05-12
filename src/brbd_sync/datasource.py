from baserowapi import Baserow
from pydantic import BaseModel, Field


class Subscriber(BaseModel):
    full_name: str
    email: str | None


class BaserowSubscriber(Subscriber):
    full_name: str = Field(alias="Full Name")
    email: str | None = Field(alias="Email")


class MailingListDatasource(BaseModel):
    subscribers: list[Subscriber]

    @classmethod
    def from_baserow_table(cls, api_key: str, table_id: int):
        baserow = Baserow(url="https://api.baserow.io", token=api_key)
        table = baserow.get_table(table_id)

        subscribers: list[Subscriber] = []
        for row in table.row_generator():
            br_sub = BaserowSubscriber(**row.to_dict())
            subscribers.append(br_sub)

        return cls(subscribers=subscribers)
