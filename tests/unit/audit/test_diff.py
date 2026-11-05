from crosserp.audit.diff import diff, diff_json


def test_diff_recursively_marks_added_deleted_and_modified() -> None:
    result = diff({"a": 1, "nested": {"old": "x"}, "gone": True}, {"a": 2, "nested": {"new": "y"}})
    assert [(item.path, item.change) for item in result] == [
        ("a", "modified"),
        ("gone", "deleted"),
        ("nested.new", "added"),
        ("nested.old", "deleted"),
    ]


def test_diff_json_handles_none_and_is_template_friendly() -> None:
    assert diff_json(None, {"amount": "1.00"}) == [
        {"path": "$", "before": None, "after": {"amount": "1.00"}, "change": "modified"}
    ]
