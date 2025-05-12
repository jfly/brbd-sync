import click

from .datasource import MailingListDatasource


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
def main(baserow_api_key: str, baserow_table_id: int):
    baserow_datasource = MailingListDatasource.from_baserow_table(
        api_key=baserow_api_key, table_id=baserow_table_id
    )
    print(baserow_datasource)
