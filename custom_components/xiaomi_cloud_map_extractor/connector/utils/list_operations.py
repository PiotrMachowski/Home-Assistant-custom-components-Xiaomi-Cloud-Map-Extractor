from functools import reduce
from typing import Any
from vacuum_map_parser_base.map_data import OutputObject


def as_list_of_dict(o_list: list[OutputObject] | None) -> list[dict[str, Any]]:
    if o_list is None:
        return []
    return [o.as_dict() if hasattr(o, "as_dict") else o for o in o_list]


def len_len(data: list[list[Any]] | None) -> int:
    return reduce(lambda count, sublist: count + len(sublist), data or [], 0)
