from textwrap import indent

import click

from brbd_sync.datasource import Subscriber

from . import baserow, buttondown


def option_with_envvar(*args, **kwargs):
    envvar = kwargs["envvar"]
    kwargs["help"] = kwargs["help"] + f" [env: {envvar}]"
    return click.option(*args, **kwargs)


class BaserowColumnNames(click.types.StringParamType):
    envvar_list_splitter = ","


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
    help="The name of a column in the Baserow table whose values should be converted to Buttondown tags. The tags will be prefixed with the name of the column. For example, if you have a column 'Hair color' with value 'red', then the resulting tag will be 'Hair color: red'. Can be repeated. If specified via environment variable, the value is split around commas (',')",
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
def main(
    baserow_api_key: str,
    baserow_table_id: int,
    baserow_tags_columns: list[str],
    baserow_metadata_columns: list[str],
    buttondown_api_key: str,
):
    baserow_datasource = baserow.load_subscribers(
        api_key=baserow_api_key,
        table_id=baserow_table_id,
        tags_column_names=baserow_tags_columns,
        metadata_column_names=baserow_metadata_columns,
    )
    buttondown_datasource = buttondown.load_subscribers(api_key=buttondown_api_key)

    baserow_ids = set(s.id for s in baserow_datasource.subscribers)
    buttondown_ids = set(s.id for s in buttondown_datasource.subscribers)
    missing = sorted(baserow_ids - buttondown_ids)
    extra = sorted(buttondown_ids - baserow_ids)

    print("### Extra ids (present in Buttondown, but not in Baserow)")
    print("\n".join(extra))

    print("### Missing ids (missing in Buttondown, but present in Baserow)")
    print("\n".join(missing))

    # Now, generate a diffs for every id that exists in both systems.
    synced_ids = sorted(baserow_ids & buttondown_ids)
    for id in synced_ids:
        baserow_sub = baserow_datasource.get_subscriber(id=id)
        buttondown_sub = buttondown_datasource.get_subscriber(id=id)

        diff = compute_diff(baserow_sub, buttondown_sub)
        if len(diff) > 0:
            print(f"Found issues with id={id}:")
            print(indent("\n".join(diff), " " * 4))


def compute_diff(baserow_sub: Subscriber, buttondown_sub: Subscriber) -> list[str]:
    diff = []

    assert baserow_sub.id == buttondown_sub.id

    # Check email.
    if baserow_sub.email != buttondown_sub.email:
        diff.append(f"Wrong email: {baserow_sub.email} != {buttondown_sub.email}")

    # Check tags.
    missings = sorted(baserow_sub.tags - buttondown_sub.tags)
    extras = sorted(buttondown_sub.tags - baserow_sub.tags)
    for missing in missings:
        diff.append(f"Missing tag {missing}")
    for extra in extras:
        diff.append(f"Extra tag {extra}")

    # Check metadata.
    br_metadata = set(baserow_sub.metadata.items())
    bd_metadata = set(buttondown_sub.metadata.items())
    missings = sorted(br_metadata - bd_metadata)
    extras = sorted(bd_metadata - br_metadata)
    for key, val in missings:
        diff.append(f"Missing metadata {key!r} = {val!r}")
    for key, val in extras:
        diff.append(f"Extra metadata {key!r} = {val!r}")

    return diff
