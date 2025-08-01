from typing import Callable


def group_by[K, V](arr: list[V], key: Callable[[V], K]) -> dict[K, list[V]]:
    result: dict[K, list[V]] = {}
    for v in arr:
        k = key(v)
        if k not in result:
            result[k] = []

        result[k].append(v)

    return result


def unique_group_by[K, V](arr: list[V], key: Callable[[V], K]) -> dict[K, V]:
    grouped = group_by(arr, key)

    result: dict[K, V] = {}

    for k, vs in grouped.items():
        assert len(vs) == 1, f"Expected to find exactly 1 value for key {k!r}: {vs}"
        (v,) = vs

        result[k] = v

    return result


def partition[V](arr: list[V], pred: Callable[[V], bool]) -> tuple[list[V], list[V]]:
    matching: list[V] = []
    not_matching: list[V] = []

    for v in arr:
        if pred(v):
            matching.append(v)
        else:
            not_matching.append(v)

    return matching, not_matching
