"""Tests for merge.py's pure line-based three-way text merge.

These tests exercise three_way_merge_lines directly -- no objects, no
filesystem, no commits -- to verify the core merge algorithm in
isolation from everything else merge.py orchestrates.
"""

from snapshot.merge import three_way_merge_lines


def _lines(text):
    return text.splitlines(keepends=True)


def test_identical_content_no_conflict():
    base = _lines("a\nb\nc\n")
    merged, conflict = three_way_merge_lines(base, base, base, "HEAD", "feature")
    assert not conflict
    assert merged == base


def test_change_on_current_only():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nB-CHANGED\nc\n")
    target = _lines("a\nb\nc\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert not conflict
    assert merged == current


def test_change_on_target_only():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nb\nc\n")
    target = _lines("a\nB-CHANGED\nc\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert not conflict
    assert merged == target


def test_non_overlapping_edits_combine():
    base = _lines("line1\nline2\nline3\nline4\nline5\n")
    current = _lines("line1\nline2-A\nline3\nline4\nline5\n")
    target = _lines("line1\nline2\nline3\nline4-B\nline5\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert not conflict
    assert merged == _lines("line1\nline2-A\nline3\nline4-B\nline5\n")


def test_overlapping_edits_conflict():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nCURRENT\nc\n")
    target = _lines("a\nTARGET\nc\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert conflict
    text = "".join(merged)
    assert "<<<<<<< HEAD\n" in text
    assert "CURRENT\n" in text
    assert "=======\n" in text
    assert "TARGET\n" in text
    assert ">>>>>>> feature\n" in text
    # unchanged context lines are still present, unmarked
    assert text.startswith("a\n")
    assert text.endswith("c\n")


def test_identical_edits_on_both_sides_no_conflict():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nSAME-CHANGE\nc\n")
    target = _lines("a\nSAME-CHANGE\nc\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert not conflict
    assert merged == current


def test_deletion_on_current_vs_modification_on_target_conflicts():
    # "modify/delete": current removed the affected region entirely,
    # target changed it -- there is no unambiguous way to combine these.
    base = _lines("a\nb\nc\n")
    current = _lines("a\nc\n")  # line "b" deleted
    target = _lines("a\nb-changed\nc\n")  # line "b" modified
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert conflict
    text = "".join(merged)
    assert "<<<<<<< HEAD" in text
    assert "b-changed" in text
    assert ">>>>>>> feature" in text


def test_multiple_independent_edits_all_combine():
    base = _lines("1\n2\n3\n4\n5\n6\n7\n")
    current = _lines("1-A\n2\n3\n4\n5\n6\n7\n")       # edit near the start
    target = _lines("1\n2\n3\n4\n5\n6\n7-B\n")         # edit near the end
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert not conflict
    assert merged == _lines("1-A\n2\n3\n4\n5\n6\n7-B\n")


def test_empty_base_both_sides_add_same_content_no_conflict():
    base = []
    current = _lines("new file\n")
    target = _lines("new file\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert not conflict
    assert merged == current


def test_empty_base_both_sides_add_different_content_conflicts():
    base = []
    current = _lines("current version\n")
    target = _lines("target version\n")
    merged, conflict = three_way_merge_lines(base, current, target, "HEAD", "feature")
    assert conflict
    text = "".join(merged)
    assert "<<<<<<< HEAD\n" in text
    assert "current version\n" in text
    assert "=======\n" in text
    assert "target version\n" in text
    assert ">>>>>>> feature\n" in text