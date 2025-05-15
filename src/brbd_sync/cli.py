import click

from . import baserow, buttondown


def option_with_envvar(*args, **kwargs):
    envvar = kwargs["envvar"]
    kwargs["help"] = kwargs["help"] + f" [env: {envvar}]"
    return click.option(*args, **kwargs)


@click.command(context_settings={"auto_envvar_prefix": "BRBD_SYNC"})
@option_with_envvar(
    "--baserow-api-key",
    required=True,
    envvar="BASEROW_API_KEY",
    help="Baserow api key.",
)
@option_with_envvar(
    "--baserow-table-id",
    type=int,
    required=True,
    envvar="BASEROW_TABLE_ID",
    help="Baserow table id.",
)
@option_with_envvar(
    "--baserow-tags-column",
    required=True,
    envvar="BASEROW_TAGS_COLUMN",
    help="The name of a column in the Baserow table whose values should be converted to Buttondown tags. The tags will be prefixed with the name of the column. For example, if you have a column 'Hair color' with value 'red', then the resulting tag will be 'Hair color: red'.",
)
@option_with_envvar(
    "--buttondown-api-key",
    required=True,
    envvar="BUTTONDOWN_API_KEY",
    help="Buttondown api id.",
)
def main(
    baserow_api_key: str,
    baserow_table_id: int,
    baserow_tags_column: str,
    buttondown_api_key: str,
):
    baserow_datasource = baserow.load_subscribers(
        api_key=baserow_api_key,
        table_id=baserow_table_id,
        tags_column_name=baserow_tags_column,
    )
    buttondown_datasource = buttondown.load_subscribers(api_key=buttondown_api_key)

    baserow_emails = set(
        s.email for s in baserow_datasource.subscribers if s.email is not None
    )
    buttondown_emails = set(
        s.email for s in buttondown_datasource.subscribers if s.email is not None
    )
    missing = sorted(baserow_emails - buttondown_emails)
    extra = sorted(buttondown_emails - baserow_emails)

    print("### Extra emails (present in Buttondown, but not in Baserow)")
    print("\n".join(extra))

    print("### Missing emails (missing in Buttondown, but present in Baserow)")
    print("\n".join(missing))

    # Now, generate a report of incorrect tags for each email that's synced.
    synced_emails = sorted(baserow_emails & buttondown_emails)
    for email in synced_emails:
        baserow_sub = baserow_datasource.get_subscriber(email=email)
        buttondown_sub = buttondown_datasource.get_subscriber(email=email)
        missing = sorted(baserow_sub.tags - buttondown_sub.tags)
        extra = sorted(buttondown_sub.tags - baserow_sub.tags)

        print(f"Buttondown subscriber {email} missing {missing}, has extra {extra}")
