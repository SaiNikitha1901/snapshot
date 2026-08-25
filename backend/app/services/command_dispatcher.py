"""The single entry point every terminal submission goes through:
parse -> call the engine (or a builtin) -> assemble one StudioResponse
that updates all five panels at once.

Calls the engine's own modules directly (blob/tree/commit/index/refs/
checkout/merge) -- the same functions `cli.py` calls, in the same
order -- rather than shelling out to the CLI and parsing its stdout,
because the frontend needs structured data, not scraped text. `cli.py`
itself is untouched.
"""

import shlex
from dataclasses import dataclass, field
from pathlib import Path

from snapshot import checkout as checkout_mod
from snapshot import commit as commit_mod
from snapshot import index as index_mod
from snapshot import merge as merge_mod
from snapshot import reflog as reflog_mod
from snapshot import refs as refs_mod
from snapshot import tree as tree_mod
from snapshot.repository import init_repository

from app.schemas.animation import AnimationSequence
from app.schemas.command import CommandMeta, StudioResponse, TerminalOutput
from app.schemas.learn import LearnCard, LearnCardSet
from app.schemas.objects import ObjectDetail
from app.services import animation_builder, builtins as builtins_mod, graph_builder, learn_service, object_serializer, status_builder

_REQUIRES_REPO = {"add", "commit", "branch", "checkout", "merge", "log", "reflog"}


@dataclass
class _CommandOutcome:
    stdout: list[str] = field(default_factory=list)
    stderr: list[str] = field(default_factory=list)
    exit_code: int = 0
    animation: AnimationSequence | None = None
    focused_object: ObjectDetail | None = None
    learn: LearnCard | None = None


def run_command(repo_root: Path, raw_input: str) -> StudioResponse:
    snapshot_dir = repo_root / ".snapshot"
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    tokens = shlex.split(raw_input) if raw_input.strip() else []
    name = tokens[0] if tokens else ""
    args = tokens[1:]

    if not tokens:
        outcome = _CommandOutcome()
        recognized = True
    elif name in _REQUIRES_REPO and not objects_dir.exists():
        outcome = _CommandOutcome(
            stderr=[
                "fatal: not a snapshot repository (.snapshot/objects not found)",
                "Run 'snapshot init' first.",
            ],
            exit_code=1,
        )
        recognized = True
    else:
        handler = _HANDLERS.get(name)
        if handler is None:
            outcome = _CommandOutcome(stderr=[f"snapshot: {name}: command not found"], exit_code=127)
            recognized = False
        else:
            try:
                outcome = handler(repo_root, snapshot_dir, objects_dir, index_path, args)
            except Exception as exc:  # a bug in one command must never break the whole studio
                outcome = _CommandOutcome(stderr=[f"snapshot: {name}: internal error: {exc}"], exit_code=1)
            recognized = True

    status = status_builder.build_status(snapshot_dir, objects_dir, index_path, repo_root)
    graph = graph_builder.build_graph(snapshot_dir, objects_dir)

    return StudioResponse(
        terminal=TerminalOutput(stdout_lines=outcome.stdout, stderr_lines=outcome.stderr, exit_code=outcome.exit_code),
        command=CommandMeta(raw_input=raw_input, name=name, args=args, recognized=recognized),
        repository_status=status,
        commit_graph=graph,
        animation=outcome.animation,
        focused_object=outcome.focused_object,
        learn=LearnCardSet(cards=[outcome.learn]) if outcome.learn else None,
    )


# --- Git-parity commands ----------------------------------------------------


def _cmd_init(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    already_initialized = objects_dir.exists()
    init_repository(repo_root)
    outcome = _CommandOutcome(stdout=[f"Initialized empty Snapshot repository in {snapshot_dir}"])
    if not already_initialized:
        outcome.animation = animation_builder.build_init_animation()
        outcome.learn = learn_service.card_for_init()
    return outcome


def _cmd_add(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    if not args:
        return _CommandOutcome(stderr=["usage: add <path>|."], exit_code=1)

    if args[0] == ".":
        targets = index_mod.collect_stageable_files(repo_root)
        if not targets:
            return _CommandOutcome(stdout=["nothing to stage"])
    else:
        try:
            target = builtins_mod.resolve_in_repo(repo_root, args[0])
        except ValueError as exc:
            return _CommandOutcome(stderr=[f"fatal: {exc}"], exit_code=1)
        if target.is_dir():
            return _CommandOutcome(
                stderr=[f"fatal: '{args[0]}' is a directory; use 'add .' to stage all project files"], exit_code=1
            )
        if not target.is_file():
            return _CommandOutcome(stderr=[f"fatal: '{args[0]}' is not a file"], exit_code=1)
        targets = [target]

    stdout = []
    staged: list[tuple[str, str]] = []
    for file_path in targets:
        try:
            entry = index_mod.stage_file(objects_dir, index_path, repo_root, file_path)
        except ValueError as exc:
            return _CommandOutcome(stdout=stdout, stderr=[f"fatal: {exc}"], exit_code=1)
        stdout.append(f"staged {entry.path}")
        staged.append((entry.path, entry.oid))

    outcome = _CommandOutcome(stdout=stdout)
    if staged:
        outcome.animation = animation_builder.build_add_animation(staged)
        outcome.focused_object = object_serializer.get_object_detail(objects_dir, staged[-1][1])
    return outcome


def _cmd_commit(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    message = _parse_message_flag(args)
    if message is None:
        return _CommandOutcome(stderr=["usage: commit -m <message>"], exit_code=1)

    entries = index_mod.read_index(index_path)
    if not entries:
        return _CommandOutcome(
            stderr=["fatal: nothing to commit (index is empty); use 'add' to stage changes first"], exit_code=1
        )

    tree_oid = tree_mod.write_tree_from_index(objects_dir, entries)

    try:
        parent_oid = refs_mod.resolve_head(snapshot_dir)
    except ValueError as exc:
        return _CommandOutcome(stderr=[f"fatal: {exc}"], exit_code=1)

    new_commit = commit_mod.build_commit(tree_oid, parent_oid, message)
    commit_oid = commit_mod.store_commit(objects_dir, new_commit)

    detached = refs_mod.is_detached(snapshot_dir)
    ref_name = None if detached else refs_mod.current_branch_name(snapshot_dir)
    reflog_prefix = "commit (initial)" if parent_oid is None else "commit"
    refs_mod.update_head(snapshot_dir, commit_oid, reflog_message=f"{reflog_prefix}: {message}")

    stdout = [commit_oid]
    if detached:
        stdout.append("Note: you are in 'detached HEAD' state; no branch was moved by this commit.")

    return _CommandOutcome(
        stdout=stdout,
        animation=animation_builder.build_commit_animation(tree_oid, commit_oid, parent_oid, ref_name, detached),
        focused_object=object_serializer.get_object_detail(objects_dir, commit_oid),
        learn=learn_service.card_for_first_commit(commit_oid, tree_oid) if parent_oid is None else None,
    )


def _cmd_branch(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    if not args:
        return _CommandOutcome(stdout=_branch_listing(snapshot_dir))

    name = args[0]
    try:
        commit_oid = refs_mod.create_branch(snapshot_dir, name)
    except ValueError as exc:
        return _CommandOutcome(stderr=[f"fatal: {exc}"], exit_code=1)

    return _CommandOutcome(
        stdout=[f"Created branch '{name}'"],
        animation=animation_builder.build_branch_animation(name, commit_oid),
        focused_object=object_serializer.get_branch_detail(snapshot_dir, name),
        learn=learn_service.card_for_branch_created(name, commit_oid),
    )


def _branch_listing(snapshot_dir: Path) -> list[str]:
    branch_names = refs_mod.list_branches(snapshot_dir)
    detached = refs_mod.is_detached(snapshot_dir)
    current = None if detached else refs_mod.current_branch_name(snapshot_dir)

    lines = []
    if detached:
        lines.append(f"* (HEAD detached at {refs_mod.resolve_head(snapshot_dir)})")
    if not branch_names:
        if not detached:
            lines.append("(no branches yet)")
    else:
        for n in branch_names:
            lines.append(f"{'*' if n == current else ' '} {n}")
    return lines


def _cmd_checkout(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    if not args:
        return _CommandOutcome(stderr=["usage: checkout <branch>|<commit>"], exit_code=1)
    target = args[0]

    was_detached = refs_mod.is_detached(snapshot_dir)
    previous_oid = refs_mod.resolve_head(snapshot_dir) if was_detached else None

    try:
        if refs_mod.branch_exists(snapshot_dir, target):
            checkout_mod.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, target)
            commit_oid = refs_mod.resolve_head(snapshot_dir)
            learn = _checkout_learn_card(
                snapshot_dir, objects_dir, was_detached, previous_oid, learn_service.card_for_checkout_branch(target)
            )
            return _CommandOutcome(
                stdout=[f"Switched to branch '{target}'"],
                animation=animation_builder.build_checkout_animation(target, True, commit_oid),
                focused_object=object_serializer.get_branch_detail(snapshot_dir, target),
                learn=learn,
            )
        commit_oid = checkout_mod.checkout_commit(snapshot_dir, objects_dir, index_path, repo_root, target)
        learn = _checkout_learn_card(
            snapshot_dir, objects_dir, was_detached, previous_oid, learn_service.card_for_detached_head(commit_oid)
        )
        return _CommandOutcome(
            stdout=[f"Note: checking out '{target}'.", f"HEAD is now detached at {commit_oid}"],
            animation=animation_builder.build_checkout_animation(target, False, commit_oid),
            focused_object=object_serializer.get_object_detail(objects_dir, commit_oid),
            learn=learn,
        )
    except ValueError as exc:
        return _CommandOutcome(stderr=[f"fatal: {exc}"], exit_code=1)


def _checkout_learn_card(snapshot_dir, objects_dir, was_detached: bool, previous_oid: str | None, default_card):
    """If HEAD was detached and the commit it pointed at just became
    unreachable as a result of this checkout, that's a more important
    teaching moment than the normal checkout/detach card -- show it
    instead (one concept at a time), right when it happens."""
    if was_detached and previous_oid:
        graph = graph_builder.build_graph(snapshot_dir, objects_dir)
        reachable_oids = {c.oid for c in graph.commits}
        if previous_oid not in reachable_oids:
            return learn_service.card_for_orphaned_commit(previous_oid)
    return default_card


def _cmd_merge(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    if not args:
        return _CommandOutcome(stderr=["usage: merge <branch>"], exit_code=1)
    target_branch = args[0]

    pre_current_oid = None
    pre_target_oid = None
    try:
        pre_current_oid = refs_mod.resolve_head(snapshot_dir)
        if refs_mod.branch_exists(snapshot_dir, target_branch):
            pre_target_oid = refs_mod.read_branch_oid(snapshot_dir / "refs" / "heads" / target_branch)
    except ValueError:
        pass  # non-critical -- only used to compute the merge base for the animation/learn card

    try:
        result = merge_mod.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, target_branch)
    except ValueError as exc:
        return _CommandOutcome(stderr=[f"fatal: {exc}"], exit_code=1)

    current_branch = refs_mod.current_branch_name(snapshot_dir)

    base_oid = None
    if pre_current_oid and pre_target_oid:
        try:
            base_oid = merge_mod.find_merge_base(objects_dir, pre_current_oid, pre_target_oid)
        except Exception:
            base_oid = None

    animation = animation_builder.build_merge_animation(
        result.kind, base_oid, current_branch, target_branch, result.commit_oid, result.conflicted_paths
    )
    learn = learn_service.card_for_merge(result.kind, current_branch, target_branch, result.commit_oid)

    if result.kind == "already_up_to_date":
        return _CommandOutcome(stdout=["Already up to date."], animation=animation, learn=learn)

    if result.kind == "fast_forward":
        return _CommandOutcome(
            stdout=[f"Fast-forward merge: branch now at {result.commit_oid}"],
            animation=animation,
            focused_object=object_serializer.get_object_detail(objects_dir, result.commit_oid),
            learn=learn,
        )

    if result.kind == "merge_commit":
        return _CommandOutcome(
            stdout=[f"Merge commit created: {result.commit_oid}"],
            animation=animation,
            focused_object=object_serializer.get_object_detail(objects_dir, result.commit_oid),
            learn=learn,
        )

    # conflict
    stderr = ["Auto-merging failed with conflicts in:"]
    stderr += [f"  both modified: {p}" for p in result.conflicted_paths]
    stderr += [
        "",
        "Snapshot (like Git) will not guess how to combine these overlapping edits. "
        "Conflict markers have been written into the file(s) above -- edit them by hand, "
        "then 'add' and 'commit' to finish.",
    ]
    return _CommandOutcome(stderr=stderr, exit_code=1, animation=animation, learn=learn)


def _cmd_log(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    try:
        current_oid = refs_mod.resolve_head(snapshot_dir)
    except ValueError as exc:
        return _CommandOutcome(stderr=[f"fatal: {exc}"], exit_code=1)
    if current_oid is None:
        return _CommandOutcome(stderr=["fatal: no commits yet"], exit_code=1)

    stdout: list[str] = []
    oid = current_oid
    while oid is not None:
        c = commit_mod.read_commit(objects_dir, oid)
        stdout.append(f"commit {oid}")
        stdout.append(f"Author: {c.author}")
        stdout.append("")
        for line in c.message.splitlines() or [""]:
            stdout.append(f"    {line}")
        stdout.append("")
        oid = c.parent
    return _CommandOutcome(stdout=stdout)


def _cmd_reflog(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    entries = list(reversed(reflog_mod.read_entries(snapshot_dir)))
    if not entries:
        return _CommandOutcome(stdout=["(reflog is empty)"])

    stdout = [f"{entry.new_oid[:7]} HEAD@{{{i}}}: {entry.message}" for i, entry in enumerate(entries)]
    return _CommandOutcome(stdout=stdout, learn=learn_service.card_for_reflog_viewed())


def _parse_message_flag(args: list[str]) -> str | None:
    for flag in ("-m", "--message"):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
    return None


# --- Filesystem builtins -----------------------------------------------------


def _from_builtin(result: builtins_mod.BuiltinResult) -> _CommandOutcome:
    return _CommandOutcome(stdout=result.stdout_lines, stderr=result.stderr_lines, exit_code=result.exit_code)


def _cmd_echo(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    return _from_builtin(builtins_mod.run_echo(repo_root, args))


def _cmd_cat(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    return _from_builtin(builtins_mod.run_cat(repo_root, args))


def _cmd_ls(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    return _from_builtin(builtins_mod.run_ls(repo_root, args))


def _cmd_mkdir(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    return _from_builtin(builtins_mod.run_mkdir(repo_root, args))


def _cmd_rm(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    return _from_builtin(builtins_mod.run_rm(repo_root, args))


def _cmd_touch(repo_root, snapshot_dir, objects_dir, index_path, args) -> _CommandOutcome:
    return _from_builtin(builtins_mod.run_touch(repo_root, args))


_HANDLERS = {
    "init": _cmd_init,
    "add": _cmd_add,
    "commit": _cmd_commit,
    "branch": _cmd_branch,
    "checkout": _cmd_checkout,
    "merge": _cmd_merge,
    "log": _cmd_log,
    "reflog": _cmd_reflog,
    "echo": _cmd_echo,
    "cat": _cmd_cat,
    "ls": _cmd_ls,
    "mkdir": _cmd_mkdir,
    "rm": _cmd_rm,
    "touch": _cmd_touch,
}
