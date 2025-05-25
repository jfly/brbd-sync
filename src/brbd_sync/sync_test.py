from . import baserow as br
from . import buttondown as bd
from .sync import sync


def br_sub(
    id: str,
    email: str,
    tags: set[str] = set(),
    metadata: dict[str, str] = {},
    full_name: str = "",
) -> br.Subscriber:
    return br.Subscriber(
        id=id,
        email=email,
        tags=tags,
        metadata={
            "id": id,
            **metadata,
        },
        **{"Full Name": full_name},
    )


def bd_sub(
    id: str,
    email: str,
    tags: set[str] = set(),
    metadata: dict[str, str] = {},
) -> bd.Subscriber:
    return bd.Subscriber(
        id=id,
        email_address=email,
        tags=tags,
        metadata={
            "id": id,
            **metadata,
        },
    )


def test_noop():
    result = sync(
        br.Data(subscribers=[br_sub(id="1", email="test1@example.com")]),
        bd.Data(subscribers=[bd_sub(id="1", email="test1@example.com")]),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == []


def test_add():
    result = sync(
        br.Data(subscribers=[br_sub(id="1", email="test1@example.com")]),
        bd.Data(subscribers=[]),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.AddSub(email="test1@example.com", metadata={"id": "1"}, tags=set())
    ]


def test_remove():
    result = sync(
        br.Data(subscribers=[]),
        bd.Data(subscribers=[bd_sub(id="1", email="test1@example.com")]),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.DeleteSub(email="test1@example.com"),
    ]


def test_missing_email_in_baserow():
    result = sync(
        br.Data(
            subscribers=[
                br_sub(id="1", email=""),
                br_sub(id="2", email=""),
            ]
        ),
        bd.Data(subscribers=[]),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == []


def test_edit_tags():
    result = sync(
        br.Data(
            subscribers=[
                br_sub(id="1", email="test1@example.com", tags={"colby", "parmesan"})
            ]
        ),
        bd.Data(
            subscribers=[bd_sub(id="1", email="test1@example.com", tags={"parmesan"})]
        ),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.EditSub(old_email="test1@example.com", tags={"colby", "parmesan"})
    ]


def test_edit_metadata():
    result = sync(
        br.Data(
            subscribers=[
                br_sub(
                    id="1", email="test1@example.com", metadata={"sport": "speedcubing"}
                )
            ]
        ),
        bd.Data(
            subscribers=[
                bd_sub(
                    id="1", email="test1@example.com", metadata={"sport": "baseball"}
                )
            ]
        ),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.EditSub(
            old_email="test1@example.com", metadata={"id": "1", "sport": "speedcubing"}
        ),
    ]


def test_edit_email():
    result = sync(
        br.Data(subscribers=[br_sub(id="1", email="test1@example.com")]),
        bd.Data(subscribers=[bd_sub(id="1", email="tst1@example.com")]),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.EditSub(old_email="tst1@example.com", new_email="test1@example.com"),
    ]


def test_edit_multiple():
    result = sync(
        br.Data(
            subscribers=[br_sub(id="1", email="test1@example.com", tags={"colby"})]
        ),
        bd.Data(
            subscribers=[bd_sub(id="1", email="tst1@example.com", tags={"parmesan"})]
        ),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.EditSub(
            old_email="tst1@example.com",
            new_email="test1@example.com",
            tags={"colby"},
        ),
    ]


def test_dupe_emails_in_baserow():
    result = sync(
        br.Data(
            subscribers=[
                br_sub(id="1", email="dupe@example.com"),
                br_sub(id="2", email="dupe@example.com"),
            ]
        ),
        bd.Data(
            subscribers=[
                bd_sub(id="2", email="dupe@example.com"),
            ],
        ),
        dry_run=True,
    )
    assert result.warnings == [
        "Unexpectedly found multiple Baserow rows with email='dupe@example.com'. I picked the one with id='1'"
    ]
    assert result.operations == [
        bd.DeleteSub(email="dupe@example.com"),
        bd.AddSub(email="dupe@example.com", metadata={"id": "1"}, tags=set()),
    ]


def test_dupe_ids_in_buttondown():
    result = sync(
        br.Data(subscribers=[br_sub(id="1", email="test1@example.com")]),
        bd.Data(
            subscribers=[
                bd_sub(id="1", email="dupe1@example.com"),
                bd_sub(id="1", email="dupe2@example.com"),
            ],
        ),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.DeleteSub(email="dupe2@example.com"),
        bd.EditSub(
            old_email="dupe1@example.com",
            new_email="test1@example.com",
        ),
    ]


def test_naive_create_would_introduce_dupe():
    # A naive implementation might first create the missing id 1 in Buttondown.
    # This wouldn't work because Buttondown doesn't allow for duplicate emails.
    # Instead, we need to first delete id 2 before creating id 1.
    result = sync(
        br.Data(subscribers=[br_sub(id="1", email="j1@example.com")]),
        bd.Data(subscribers=[bd_sub(id="2", email="j1@example.com")]),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.DeleteSub(email="j1@example.com"),
        bd.AddSub(email="j1@example.com", metadata={"id": "1"}, tags=set()),
    ]


def test_swap_email():
    result = sync(
        br.Data(
            subscribers=[
                br_sub(id="1", email="j1@example.com"),
                br_sub(id="2", email="j2@example.com"),
            ]
        ),
        bd.Data(
            subscribers=[
                bd_sub(id="1", email="j2@example.com"),
                bd_sub(id="2", email="j1@example.com"),
            ]
        ),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.DeleteSub(email="j1@example.com"),
        bd.EditSub(old_email="j2@example.com", new_email="j1@example.com"),
        bd.AddSub(email="j2@example.com", metadata={"id": "2"}, tags=set()),
    ]


def test_confusing_delete_and_edit_email():
    result = sync(
        br.Data(
            subscribers=[
                br_sub(id="1", email="j1@example.com"),
            ]
        ),
        bd.Data(
            subscribers=[
                bd_sub(id="1", email="j2@example.com"),
                bd_sub(id="2", email="j1@example.com"),
            ]
        ),
        dry_run=True,
    )
    assert result.warnings == []
    assert result.operations == [
        bd.DeleteSub(email="j1@example.com"),
        bd.EditSub(old_email="j2@example.com", new_email="j1@example.com"),
    ]
