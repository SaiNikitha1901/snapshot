"""Merge: combining two branches' histories into one snapshot.

Git does not merge files directly. It merges HISTORIES: it finds the
closest common ancestor of two commits (the "merge base"), then asks
"what changed between the base and each side, independently," and
tries to combine those two independent change sets into one merged
snapshot. The result is recorded as an ordinary commit -- the only
thing distinguishing a "merge commit" from any other commit is that
it has two parents instead of one (see commit.py's `merge_parent`).

This module orchestrates existing infrastructure -- object storage,
tree construction/parsing, commit creation, checkout's restoration
logic -- rather than reimplementing any of it. The only genuinely new
logic here is: (1) finding the merge base by walking ancestors, and
(2) an educational three-way text merge using difflib.

Known simplification: Snapshot's line-level merge does not specially
handle the rare case of both sides inserting new content at exactly
the same position within a file that already existed in the base
(with no other nearby change). Production Git treats this as an
ordering ambiguity; Snapshot may apply both insertions in an arbitrary
order rather than flag a conflict. The far more common and more
important cases -- edits to different lines, edits to the same line,
one-sided edits, and two branches independently creating the same new
file -- are all handled correctly and are what the test suite and the
manual experiment below exercise.
"""

import difflib
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from . import checkout, commit, objects, refs, tree
from .index import IndexEntry


@dataclass
class MergeResult:
    """What happened as a result of `merge_branch`.

    kind is one of: "already_up_to_date", "fast_forward", "merge_commit", "conflict".
    commit_oid is set for every kind except "conflict".
    conflicted_paths is set only for "conflict".
    """

    kind: str
    commit_oid: str | None = None
    conflicted_paths: list[str] = field(default_factory=list)


# --- Merge base -------------------------------------------------------


def _all_ancestors(objects_dir: Path, commit_oid: str) -> set[str]:
    """Return every commit OID reachable from commit_oid by following
    parent links (both parents, for merge commits), including
    commit_oid itself.
    """
    visited: set[str] = set()
    frontier = [commit_oid]
    while frontier:
        oid = frontier.pop()
        if oid in visited:
            continue
        visited.add(oid)
        commit_obj = commit.read_commit(objects_dir, oid)
        if commit_obj.parent is not None:
            frontier.append(commit_obj.parent)
        if commit_obj.merge_parent is not None:
            frontier.append(commit_obj.merge_parent)
    return visited


def find_merge_base(objects_dir: Path, current_oid: str, target_oid: str) -> str | None:
    """Find the closest common ancestor of two commits.

    Educational algorithm, favoring clarity over Git's actual
    optimized approach: compute the full set of current's ancestors,
    then walk target's ancestors breadth-first (closest first) and
    return the first one that's also an ancestor of current.

    Returns None only if the two commits share no ancestor at all --
    which shouldn't happen for any two branches created through
    Snapshot's own `branch`/`commit` commands, since every branch
    traces back to the same first commit, but is handled defensively.
    """
    current_ancestors = _all_ancestors(objects_dir, current_oid)

    visited: set[str] = set()
    queue = deque([target_oid])
    while queue:
        oid = queue.popleft()
        if oid in visited:
            continue
        visited.add(oid)
        if oid in current_ancestors:
            return oid
        commit_obj = commit.read_commit(objects_dir, oid)
        if commit_obj.parent is not None:
            queue.append(commit_obj.parent)
        if commit_obj.merge_parent is not None:
            queue.append(commit_obj.merge_parent)
    return None


# --- Three-way text merge (the only genuinely new algorithm here) -----


def _cluster_hunks(hunks_a, hunks_b) -> list[tuple[int, int, list[tuple[str, int, int, int, int]]]]:
    """Merge hunks from both sides into clusters of overlapping base ranges.

    Each cluster is (lo, hi, members), where members is a list of
    (side, i1, i2, j1, j2) for every hunk (from either side) whose base
    range falls inside [lo, hi). Hunks from the SAME side never overlap
    each other (they come from a single diff's opcodes, which partition
    the base into non-overlapping ranges); a cluster only ever grows
    past a single hunk when a hunk from the OTHER side bridges the gap.
    This is the standard "merge overlapping intervals" sweep: sort by
    start, then extend the last cluster whenever the next range begins
    before it ends.

    One deliberate special case: a hunk with i1 == i2 is a pure
    insertion -- it doesn't span any base line, it happens "between"
    two base positions. Two insertions from different sides at the
    exact same base position can't be ordered by base-line comparison
    at all, so they're treated as touching (not just overlapping) --
    otherwise two sides inserting the same content at the same spot
    would (wrongly) look like two independent, combinable edits instead
    of one shared one.
    """
    tagged = [("a", i1, i2, j1, j2) for (i1, i2, j1, j2) in hunks_a]
    tagged += [("b", i1, i2, j1, j2) for (i1, i2, j1, j2) in hunks_b]
    tagged.sort(key=lambda h: h[1])

    clusters: list[list] = []  # each entry: [lo, hi, members, hi_is_pure_insertion]
    for side, i1, i2, j1, j2 in tagged:
        is_insertion = i1 == i2
        if clusters:
            lo, hi, members, hi_is_insertion = clusters[-1]
            touches = i1 < hi or (i1 == hi and (is_insertion or hi_is_insertion))
        else:
            touches = False

        if touches:
            lo, hi, members, hi_is_insertion = clusters[-1]
            if i2 > hi:
                new_hi, new_hi_is_insertion = i2, is_insertion
            elif i2 < hi:
                new_hi, new_hi_is_insertion = hi, hi_is_insertion
            else:
                new_hi, new_hi_is_insertion = hi, hi_is_insertion or is_insertion
            clusters[-1] = [lo, new_hi, members + [(side, i1, i2, j1, j2)], new_hi_is_insertion]
        else:
            clusters.append([i1, i2, [(side, i1, i2, j1, j2)], is_insertion])

    return [(lo, hi, members) for lo, hi, members, _ in clusters]


def _extract_side_content(opcodes, lo: int, hi: int, other_lines: list[str]) -> list[str]:
    """Reconstruct the 'other' (current or target) content corresponding
    to base range [lo, hi), using the FULL opcode list (including
    'equal' opcodes) for base->other.

    'equal' opcodes have an exact positional correspondence between
    base and other, so a partial sub-range can be taken safely. A
    non-equal opcode can never be partially cut by a cluster boundary
    (clusters are built to fully contain every hunk in them -- see
    _cluster_hunks), so non-equal opcodes are always included whole.

    A zero-width cluster (lo == hi) represents a pure-insertion point
    rather than a range of base lines, so it's matched against opcodes
    that insert at exactly that point instead of using the normal
    overlap test (which can never be satisfied by an empty range).
    """
    result: list[str] = []
    for tag, i1, i2, j1, j2 in opcodes:
        if lo == hi:
            if i1 == i2 == lo and tag != "equal":
                result.extend(other_lines[j1:j2])
            continue
        if i2 <= lo or i1 >= hi:
            continue
        if tag == "equal":
            start, end = max(lo, i1), min(hi, i2)
            offset = j1 - i1
            result.extend(other_lines[start + offset:end + offset])
        else:
            result.extend(other_lines[j1:j2])
    return result


def three_way_merge_lines(
    base_lines: list[str],
    current_lines: list[str],
    target_lines: list[str],
    current_label: str,
    target_label: str,
) -> tuple[list[str], bool]:
    """Educational three-way line merge, using only difflib from the
    standard library.

    Walks base left to right. Base ranges untouched by either side pass
    through unchanged. A range changed by only one side takes that
    side's content. A range changed by both sides is checked: if both
    sides ended up with identical content there, no conflict; otherwise
    the region is wrapped in Git-style conflict markers.

    Returns (merged_lines, has_conflict).
    """
    ops_a = list(difflib.SequenceMatcher(None, base_lines, current_lines, autojunk=False).get_opcodes())
    ops_b = list(difflib.SequenceMatcher(None, base_lines, target_lines, autojunk=False).get_opcodes())

    hunks_a = [(i1, i2, j1, j2) for tag, i1, i2, j1, j2 in ops_a if tag != "equal"]
    hunks_b = [(i1, i2, j1, j2) for tag, i1, i2, j1, j2 in ops_b if tag != "equal"]

    clusters = _cluster_hunks(hunks_a, hunks_b)

    merged: list[str] = []
    has_conflict = False
    pos = 0

    for lo, hi, members in clusters:
        merged.extend(base_lines[pos:lo])

        sides_present = {m[0] for m in members}

        if sides_present == {"a"}:
            _, i1, i2, j1, j2 = members[0]  # exactly one member -- see _cluster_hunks docstring
            merged.extend(current_lines[j1:j2])
        elif sides_present == {"b"}:
            _, i1, i2, j1, j2 = members[0]
            merged.extend(target_lines[j1:j2])
        else:
            current_side = _extract_side_content(ops_a, lo, hi, current_lines)
            target_side = _extract_side_content(ops_b, lo, hi, target_lines)
            if current_side == target_side:
                merged.extend(current_side)
            else:
                has_conflict = True
                merged.append(f"<<<<<<< {current_label}\n")
                merged.extend(current_side)
                merged.append("=======\n")
                merged.extend(target_side)
                merged.append(f">>>>>>> {target_label}\n")

        pos = hi

    merged.extend(base_lines[pos:])
    return merged, has_conflict


# --- Tree merge ---------------------------------------------------------


def _read_blob_or_empty(objects_dir: Path, entry: IndexEntry | None) -> bytes:
    if entry is None:
        return b""
    _, content = objects.read_object(objects_dir, entry.oid)
    return content


def _whole_file_conflict(
    current_content: bytes, target_content: bytes, current_label: str, target_label: str
) -> bytes:
    """Wrap two entire file versions in Git-style conflict markers.

    Used when there's no shared base content to diff line-by-line
    against -- e.g. two branches independently added a file at the same
    path -- and for binary content, where a line-level merge doesn't
    make sense.
    """
    parts = [f"<<<<<<< {current_label}\n".encode(), current_content]
    if current_content and not current_content.endswith(b"\n"):
        parts.append(b"\n")
    parts.append(b"=======\n")
    parts.append(target_content)
    if target_content and not target_content.endswith(b"\n"):
        parts.append(b"\n")
    parts.append(f">>>>>>> {target_label}\n".encode())
    return b"".join(parts)


def _merge_file(
    objects_dir: Path,
    path: str,
    current_entry: IndexEntry | None,
    target_entry: IndexEntry | None,
    base_entry: IndexEntry | None,
    current_label: str,
    target_label: str,
) -> tuple[IndexEntry | None, bytes | None]:
    """Three-way merge a single existing file's content (base_entry is
    known to be present -- add/add is handled separately by the caller).

    Returns (merged_entry, conflict_content):
      - clean merge: (IndexEntry for a newly stored blob, None)
      - conflict:    (None, conflict-marker-annotated bytes to write
                       into the working directory)
    """
    base_content = _read_blob_or_empty(objects_dir, base_entry)
    current_content = _read_blob_or_empty(objects_dir, current_entry)
    target_content = _read_blob_or_empty(objects_dir, target_entry)

    try:
        base_text = base_content.decode()
        current_text = current_content.decode()
        target_text = target_content.decode()
    except UnicodeDecodeError:
        # Binary content -- line-level merging doesn't apply (out of scope).
        return None, _whole_file_conflict(current_content, target_content, current_label, target_label)

    merged_lines, has_conflict = three_way_merge_lines(
        base_text.splitlines(keepends=True),
        current_text.splitlines(keepends=True),
        target_text.splitlines(keepends=True),
        current_label, target_label,
    )
    merged_bytes = "".join(merged_lines).encode()

    if has_conflict:
        return None, merged_bytes

    mode = current_entry.mode if current_entry is not None else target_entry.mode
    new_oid = objects.write_object(objects_dir, "blob", merged_bytes)
    return IndexEntry(path=path, mode=mode, oid=new_oid), None


def _write_conflict_to_working_directory(repo_root: Path, path: str, content: bytes) -> None:
    file_path = repo_root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)


def _merge_trees(
    objects_dir: Path,
    base_entries: list[IndexEntry],
    current_entries: list[IndexEntry],
    target_entries: list[IndexEntry],
    current_label: str,
    target_label: str,
    repo_root: Path,
) -> tuple[list[IndexEntry], list[str]]:
    """Compute the merged set of tree entries for every path touched by
    either side, relative to their common base.

    Returns (merged_entries, conflicted_paths). If conflicted_paths is
    non-empty, merged_entries should be ignored by the caller -- the
    merge failed, and conflict markers have already been written into
    the working directory for each conflicted path.
    """
    base_map = {e.path: e for e in base_entries}
    current_map = {e.path: e for e in current_entries}
    target_map = {e.path: e for e in target_entries}

    all_paths = sorted(set(base_map) | set(current_map) | set(target_map))

    merged_entries: list[IndexEntry] = []
    conflicted_paths: list[str] = []

    for path in all_paths:
        base_entry = base_map.get(path)
        current_entry = current_map.get(path)
        target_entry = target_map.get(path)

        base_oid = base_entry.oid if base_entry else None
        current_oid = current_entry.oid if current_entry else None
        target_oid = target_entry.oid if target_entry else None

        if current_oid == target_oid:
            # Both sides agree -- including both deleting it, both
            # leaving it unchanged, or both making the identical edit.
            if current_entry is not None:
                merged_entries.append(current_entry)
            continue

        if current_oid == base_oid:
            # Unchanged on current -- take whatever target did (incl. deletion).
            if target_entry is not None:
                merged_entries.append(target_entry)
            continue

        if target_oid == base_oid:
            # Unchanged on target -- take whatever current did (incl. deletion).
            if current_entry is not None:
                merged_entries.append(current_entry)
            continue

        if base_entry is None:
            # Both sides independently created this path with different
            # content. There's no shared base to compute independent
            # changes against, so this is always a conflict.
            conflicted_paths.append(path)
            conflict_bytes = _whole_file_conflict(
                _read_blob_or_empty(objects_dir, current_entry),
                _read_blob_or_empty(objects_dir, target_entry),
                current_label, target_label,
            )
            _write_conflict_to_working_directory(repo_root, path, conflict_bytes)
            continue

        # Both sides modified an existing file differently -- attempt a
        # line-level three-way merge.
        merged_entry, conflict_content = _merge_file(
            objects_dir, path, current_entry, target_entry, base_entry, current_label, target_label,
        )
        if conflict_content is not None:
            conflicted_paths.append(path)
            _write_conflict_to_working_directory(repo_root, path, conflict_content)
        else:
            merged_entries.append(merged_entry)

    return merged_entries, conflicted_paths


def _tree_entries_for_commit(objects_dir: Path, commit_oid: str) -> list[IndexEntry]:
    commit_obj = commit.read_commit(objects_dir, commit_oid)
    return tree.flatten_tree_to_entries(objects_dir, commit_obj.tree)


# --- Orchestration --------------------------------------------------------


def merge_branch(
    snapshot_dir: Path, objects_dir: Path, index_path: Path, repo_root: Path, target_branch_name: str
) -> MergeResult:
    """Merge target_branch_name into the current branch.

    Raises:
        ValueError: the target branch doesn't exist, HEAD is detached,
            the target is the current branch, the current branch has
            no commits, there's uncommitted local work, or (in a
            pathological repository) no common ancestor exists.
    """
    if not refs.branch_exists(snapshot_dir, target_branch_name):
        raise ValueError(f"branch '{target_branch_name}' does not exist")

    if refs.is_detached(snapshot_dir):
        raise ValueError("cannot merge while HEAD is detached; checkout a branch first")

    current_branch_name = refs.current_branch_name(snapshot_dir)
    if target_branch_name == current_branch_name:
        raise ValueError(f"cannot merge branch '{target_branch_name}' into itself")

    current_oid = refs.resolve_head(snapshot_dir)
    if current_oid is None:
        raise ValueError("cannot merge: current branch has no commits yet")

    target_oid = refs.read_branch_oid(snapshot_dir / "refs" / "heads" / target_branch_name)

    if current_oid == target_oid:
        return MergeResult(kind="already_up_to_date", commit_oid=current_oid)

    # Refuse to merge over uncommitted local work, exactly like checkout does
    # -- reusing the same two checks rather than reimplementing them.
    if checkout.unstaged_changes_exist(repo_root, index_path):
        raise ValueError(
            "cannot merge: you have uncommitted changes in your working "
            "directory; commit or discard them first"
        )
    if checkout.staged_changes_exist(objects_dir, index_path, current_oid):
        raise ValueError(
            "cannot merge: you have staged changes that haven't been "
            "committed; commit or unstage them first"
        )

    base_oid = find_merge_base(objects_dir, current_oid, target_oid)
    if base_oid is None:
        raise ValueError(
            f"cannot merge: no common ancestor found between "
            f"'{current_branch_name}' and '{target_branch_name}'"
        )

    if base_oid == target_oid:
        # current already contains everything target has.
        return MergeResult(kind="already_up_to_date", commit_oid=current_oid)

    if base_oid == current_oid:
        # Fast-forward: current is strictly behind target. Only the
        # branch pointer moves -- no tree, no commit, no new object of
        # any kind is created.
        refs.update_head(snapshot_dir, target_oid)
        checkout.restore_to_commit(objects_dir, index_path, repo_root, target_oid)
        return MergeResult(kind="fast_forward", commit_oid=target_oid)

    # True three-way merge: histories have diverged.
    base_entries = _tree_entries_for_commit(objects_dir, base_oid)
    current_entries = _tree_entries_for_commit(objects_dir, current_oid)
    target_entries = _tree_entries_for_commit(objects_dir, target_oid)

    merged_entries, conflicted_paths = _merge_trees(
        objects_dir, base_entries, current_entries, target_entries,
        current_label="HEAD", target_label=target_branch_name, repo_root=repo_root,
    )

    if conflicted_paths:
        return MergeResult(kind="conflict", conflicted_paths=sorted(conflicted_paths))

    merged_tree_oid = tree.write_tree_from_index(objects_dir, merged_entries)

    merge_commit = commit.build_commit(
        merged_tree_oid,
        current_oid,
        f"Merge {target_branch_name} into {current_branch_name}",
        merge_parent_oid=target_oid,
    )
    merge_commit_oid = commit.store_commit(objects_dir, merge_commit)

    refs.update_head(snapshot_dir, merge_commit_oid)
    checkout.restore_to_commit(objects_dir, index_path, repo_root, merge_commit_oid)

    return MergeResult(kind="merge_commit", commit_oid=merge_commit_oid)