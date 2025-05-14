from pydantic import BaseModel


class Subscriber(BaseModel):
    full_name: str
    email: str | None


class MailingListDatasource(BaseModel):
    subscribers: list[Subscriber]
