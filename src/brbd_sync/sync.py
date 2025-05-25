import click
from pydantic import BaseModel

from brbd_sync import buttondown_api

from . import baserow as br
from . import buttondown as bd
from . import buttondown_api as bd_api

SyncOperation = buttondown_api.Operation


class SyncResult(BaseModel):
    warnings: list[str] = []
    operations: list[SyncOperation] = []

    def add_warning(self, warning: str):
        click.secho(warning, fg="yellow")
        self.warnings.append(warning)

    def add_op(self, op: SyncOperation):
        click.echo(f"Operation {type(op).__name__}: {op}")
        self.operations.append(op)


def sync(
    baserow_data_possible_email_dupes: br.Data,
    buttondown_data: bd.Data,
    dry_run: bool,
) -> SyncResult:
    result = SyncResult()

    dupe_emails, baserow_data = (
        baserow_data_possible_email_dupes.with_no_duplicate_emails()
    )
    for dupe_email in dupe_emails:
        row = baserow_data.get_subscriber(email=dupe_email)
        assert row is not None
        result.add_warning(
            f"Unexpectedly found multiple Baserow rows with email={dupe_email!r}. I picked the one with id={row.id!r}"
        )

    baserow_ids = set(s.id for s in baserow_data.subscribers)
    buttondown_ids = set(s.id for s in buttondown_data.subscribers)

    for id in sorted(baserow_ids | buttondown_ids):
        baserow_sub = baserow_data.get_subscriber(id=id)
        buttondown_subs = buttondown_data.get_subscribers(id=id)

        # No such id in Baserow -> delete all Buttondown subs.
        if baserow_sub is None:
            for bd_sub_to_remove in buttondown_subs:
                delete_op = bd_api.DeleteSub(email=bd_sub_to_remove.email)
                result.add_op(delete_op)
                buttondown_data.delete(delete_op, dry_run=dry_run)

            continue

        # The interesting part: there's a row in Baserow, we need to make
        # sure there's a corresponding row in Buttondown.

        # First, make sure that the desired email is not present in Buttondown.
        # If it is, we need to first remove it so we don't try to create a dupe
        # email in Buttondown (which is not allowed).
        bd_sub_with_email = buttondown_data.get_subscriber(email=baserow_sub.email)

        if bd_sub_with_email is not None and bd_sub_with_email.id != baserow_sub.id:
            delete_op = bd_api.DeleteSub(email=bd_sub_with_email.email)
            result.add_op(delete_op)
            buttondown_data.delete(delete_op, dry_run=dry_run)

        # No such id in Buttondown -> create it!
        if len(buttondown_subs) == 0:
            edit_op = bd_api.AddSub(
                email=baserow_sub.email,
                tags=baserow_sub.tags,
                metadata=baserow_sub.metadata,
            )
            result.add_op(edit_op)
            buttondown_data.add(edit_op, dry_run=dry_run)
            continue

        # If there are multiple Buttondown subs with the same id,
        # delete all but the first one.
        buttondown_sub, *bd_subs_to_remove = buttondown_subs
        for bd_sub_to_remove in bd_subs_to_remove:
            delete_op = bd_api.DeleteSub(email=bd_sub_to_remove.email)
            result.add_op(delete_op)
            buttondown_data.delete(delete_op, dry_run=dry_run)

        # We've got a matching row from Baserow and a subscription
        # from Buttondown -> edit the subscription in Buttondown to match.
        edit_op = bd_api.EditSub(old_email=buttondown_sub.email)
        if baserow_sub.email != buttondown_sub.email:
            edit_op.new_email = baserow_sub.email

        if baserow_sub.tags != buttondown_sub.tags:
            edit_op.tags = baserow_sub.tags

        if baserow_sub.metadata != buttondown_sub.metadata:
            edit_op.metadata = baserow_sub.metadata

        if not edit_op.is_noop():
            result.add_op(edit_op)
            buttondown_data.edit(edit_op, dry_run=dry_run)

    return result
