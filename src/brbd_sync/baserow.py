from baserowapi import Baserow
from pydantic import Field

from .datasource import MailingListDatasource, Subscriber


class BaserowSubscriber(Subscriber):
    full_name: str = Field(alias="Full Name")


def load_subscribers(
    api_key: str,
    table_id: int,
    tags_column_names: list[str],
    metadata_column_names: list[str],
) -> MailingListDatasource:
    baserow = Baserow(url="https://api.baserow.io", token=api_key)
    table = baserow.get_table(table_id)

    subscribers: list[Subscriber] = []
    for row in table.row_generator():
        tags = set(
            f"{tags_column_name}: {tag}"
            for tags_column_name in tags_column_names
            for tag in row[tags_column_name]
        )

        metadata = {
            metadata_key: row[metadata_key] for metadata_key in metadata_column_names
        }

        concated_emails = row["Email"]
        emails = [email.strip() for email in concated_emails.split(";")]

        for email in emails:
            br_sub = BaserowSubscriber(
                **row.to_dict(), tags=tags, email=email, metadata=metadata
            )
            subscribers.append(br_sub)

    return MailingListDatasource(description="Baserow", subscribers=subscribers)
