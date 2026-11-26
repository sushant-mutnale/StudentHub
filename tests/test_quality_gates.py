from scripts.check_quality_gates import new_findings


def test_new_findings_are_returned():
    current = [
        "backend/main.py:1:1: F401 unused import",
        "backend/main.py:2:1: E501 line too long",
        "Success: no issues found",
    ]
    baseline = ["backend/main.py:1:1: F401 unused import"]

    assert new_findings(current, baseline) == [
        "backend/main.py:2:1: E501 line too long"
    ]


def test_summary_lines_are_ignored():
    current = [
        "Found 7 errors in 4 files (checked 30 source files)",
        "Success: no issues found in 30 source files",
    ]

    assert new_findings(current, []) == []


def test_posix_current_matches_windows_baseline():
    current = ["backend/main.py:1:1: F401 unused import"]
    baseline = ["backend\\main.py:1:1: F401 unused import"]

    assert new_findings(current, baseline) == []


def test_windows_current_matches_posix_baseline():
    current = ["backend\\main.py:1:1: F401 unused import"]
    baseline = ["backend/main.py:1:1: F401 unused import"]

    assert new_findings(current, baseline) == []
