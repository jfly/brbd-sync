import logging
from typing import Any

import click

from . import baserow, buttondown, buttondown_api
from .sync import sync


def option_with_envvar(*args, **kwargs):
    envvar = kwargs["envvar"]
    kwargs["help"] = kwargs["help"] + f" [env: {envvar}]"
    return click.option(*args, **kwargs)


class BaserowColumnNames(click.types.StringParamType):
    envvar_list_splitter = ","


def prompt(
    msg: str, choices: dict[str, Any]
) -> bool:  # pragma: no cover (too lazy to test)
    choices = {label.lower(): value for label, value in choices.items()}
    choices_str = "/".join(choices.keys())

    answer = None
    while answer is None:
        response = input(msg + f" [{choices_str}] ")
        value = choices.get(response.lower())
        if value is not None:
            return value

        if response:
            click.echo(f"{response!r} is not a valid choice!")

    return True


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
    "baserow_tags_columns",
    "--baserow-tags-column",
    multiple=True,
    type=BaserowColumnNames(),
    envvar="BASEROW_TAGS_COLUMNS",
    help="The name of a column in the Baserow table whose values should be converted to Buttondown tags. Can be repeated. If specified via environment variable, the value is split around commas (',')",
)
@option_with_envvar(
    "baserow_metadata_columns",
    "--baserow-metadata-column",
    multiple=True,
    type=BaserowColumnNames(),
    envvar="BASEROW_METADATA_COLUMNS",
    help="The name of a column in the Baserow table whose values should be converted to Buttondown metadatas. The metadata key will be the name of the column, and the value will be the singleton value in the cell. It is an error to use a column whose values are lists. For example, if you have a column 'Hair color' with value 'red', then the resulting metadata will be key='Hair color', and value='red'. Can be repeated. If specified via environment variable, the value is split around commas (',')",
)
@option_with_envvar(
    "--buttondown-api-key",
    required=True,
    envvar="BUTTONDOWN_API_KEY",
    help="Buttondown api id.",
)
@option_with_envvar(
    "--dry-run/--no-dry-run",
    default=None,
    envvar="BUTTONDOWN_DRY_RUN",
    help="Do not change anything, only print out a list of what would happen.",
)
def main(
    baserow_api_key: str,
    baserow_table_id: int,
    baserow_tags_columns: list[str],
    baserow_metadata_columns: list[str],
    buttondown_api_key: str,
    dry_run: bool | None,
):  # pragma: no cover (requires internet)
    logging.basicConfig()

    if dry_run is None:
        dry_run = prompt("Dry run?", {"Y": True, "n": False})

    if dry_run:
        click.secho("Doing a dry run", fg="yellow")

    baserow_data = baserow.Data.load(
        api_key=baserow_api_key,
        table_id=baserow_table_id,
        tags_column_names=baserow_tags_columns,
        metadata_column_names=baserow_metadata_columns,
    )
    buttondown_data = buttondown.Data.load(
        api_client=buttondown_api.Client(buttondown_api_key)
    )

    sync_result = sync(baserow_data, buttondown_data, dry_run=dry_run)

    if len(sync_result.warnings) == 0:
        success_prefix = '"Succeeded" (this was a dry run)' if dry_run else "Succeeded"
        click.secho(
            f"{success_prefix} after {len(sync_result.operations)} operation(s). See above for details.",
            fg="green",
        )
    else:
        click.secho(
            f"Performed {len(sync_result.operations)} operation(s), but encountered {len(sync_result.warnings)} warning(s). See above for details.",
            fg="yellow",
        )
