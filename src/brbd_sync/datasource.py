from pydantic import BaseModel


class Subscriber(BaseModel):
    email: str | None


class MailingListDatasource(BaseModel):
    subscribers: list[Subscriber]
