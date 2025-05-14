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
    "--buttondown-api-key",
    required=True,
    envvar="BUTTONDOWN_API_KEY",
    help="Buttondown api id.",
)
def main(baserow_api_key: str, baserow_table_id: int, buttondown_api_key: str):
    baserow_datasource = baserow.load_subscribers(
        api_key=baserow_api_key, table_id=baserow_table_id
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
