"""Builds the ordered AnimationStep[] for each command kind -- the
"what happened internally" timeline the Object Animation Pipeline
plays. Each function here is a pure translation from the already-
computed result of a command_dispatcher call into a sequence of
steps; it performs no engine calls itself.
"""

from app.schemas.animation import AnimationSequence, AnimationStep


def build_init_animation() -> AnimationSequence:
    return AnimationSequence(
        command="init",
        steps=[
            AnimationStep(
                kind="init_repository",
                label="Create .snapshot/objects and refs/heads/",
                detail="An empty content-addressable object store, ready to hold blobs, trees, and commits.",
            ),
        ],
    )


def build_add_animation(staged: list[tuple[str, str]]) -> AnimationSequence:
    """staged: list of (path, blob_oid) for every file just staged."""
    steps: list[AnimationStep] = []
    for path, oid in staged:
        steps.append(
            AnimationStep(
                kind="hash_blob",
                label=f"Hash {path}",
                detail="SHA-1 of \"blob <size>\\0<content>\" -- the file's content, not its name or location.",
                object_oid=oid,
                object_type="blob",
                path=path,
            )
        )
        steps.append(
            AnimationStep(
                kind="write_object",
                label=f"Store blob {oid[:7]}",
                object_oid=oid,
                object_type="blob",
                path=path,
            )
        )
        steps.append(
            AnimationStep(
                kind="update_index",
                label=f"Record {path} in the index",
                path=path,
                object_oid=oid,
            )
        )
    return AnimationSequence(command="add", steps=steps)


def build_commit_animation(
    tree_oid: str, commit_oid: str, parent_oid: str | None, ref_name: str | None, detached: bool
) -> AnimationSequence:
    steps = [
        AnimationStep(
            kind="build_tree",
            label="Build tree from staged files",
            object_oid=tree_oid,
            object_type="tree",
        ),
        AnimationStep(
            kind="write_commit",
            label="Write commit object",
            detail=f"Points at tree {tree_oid[:7]}" + (f" and parent {parent_oid[:7]}" if parent_oid else " (first commit, no parent)"),
            object_oid=commit_oid,
            object_type="commit",
        ),
    ]
    if detached:
        steps.append(
            AnimationStep(kind="move_head", label="Move detached HEAD", detail="No branch moves.", object_oid=commit_oid)
        )
    else:
        steps.append(
            AnimationStep(
                kind="update_ref", label=f"Advance branch '{ref_name}'", ref_name=ref_name, object_oid=commit_oid
            )
        )
    return AnimationSequence(command="commit", steps=steps)


def build_branch_animation(name: str, commit_oid: str) -> AnimationSequence:
    return AnimationSequence(
        command="branch",
        steps=[
            AnimationStep(
                kind="create_branch_ref",
                label=f"Create refs/heads/{name}",
                detail="A lightweight pointer -- one small file, no objects touched.",
                ref_name=name,
                object_oid=commit_oid,
            ),
        ],
    )


def build_checkout_animation(target: str, is_branch: bool, commit_oid: str) -> AnimationSequence:
    steps = [
        AnimationStep(
            kind="restore_working_directory",
            label="Restore working directory + index from target tree",
            object_oid=commit_oid,
        ),
    ]
    if is_branch:
        steps.append(AnimationStep(kind="move_head", label=f"Point HEAD at branch '{target}'", ref_name=target))
    else:
        steps.append(
            AnimationStep(kind="move_head", label="Detach HEAD onto this commit", detail="HEAD now holds a raw OID, not a branch name.", object_oid=commit_oid)
        )
    return AnimationSequence(command="checkout", steps=steps)


def build_merge_animation(
    kind: str,
    base_oid: str | None,
    current_branch: str,
    target_branch: str,
    commit_oid: str | None,
    conflicted_paths: list[str],
) -> AnimationSequence:
    steps: list[AnimationStep] = []
    if base_oid is not None:
        steps.append(
            AnimationStep(
                kind="find_merge_base",
                label=f"Find merge base of '{current_branch}' and '{target_branch}'",
                object_oid=base_oid,
                object_type="commit",
            )
        )

    if kind == "already_up_to_date":
        return AnimationSequence(command="merge", steps=steps)

    if kind == "fast_forward":
        steps.append(
            AnimationStep(
                kind="fast_forward",
                label=f"Fast-forward '{current_branch}' to {commit_oid[:7] if commit_oid else ''}",
                detail="No new commit -- the branch pointer simply advances.",
                object_oid=commit_oid,
                ref_name=current_branch,
            )
        )
        steps.append(AnimationStep(kind="restore_working_directory", label="Restore working directory + index"))
        return AnimationSequence(command="merge", steps=steps)

    steps.append(AnimationStep(kind="diff_three_way", label="Diff base -> current and base -> target independently"))

    if kind == "conflict":
        for path in conflicted_paths:
            steps.append(AnimationStep(kind="conflict_marker", label=f"Overlapping edit in {path}", path=path))
        return AnimationSequence(command="merge", steps=steps)

    # merge_commit
    steps.append(AnimationStep(kind="build_tree", label="Build merged tree"))
    steps.append(
        AnimationStep(
            kind="write_commit",
            label="Write merge commit (two parents)",
            object_oid=commit_oid,
            object_type="commit",
        )
    )
    steps.append(AnimationStep(kind="update_ref", label=f"Advance '{current_branch}'", ref_name=current_branch, object_oid=commit_oid))
    steps.append(AnimationStep(kind="restore_working_directory", label="Restore working directory + index"))
    return AnimationSequence(command="merge", steps=steps)
