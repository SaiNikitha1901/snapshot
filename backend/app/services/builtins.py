"""POSIX-ish terminal builtins: echo, cat, ls, mkdir, rm, touch.

The spec's terminal is Git-only by default, but there is no separate
file-editor panel in Snapshot Studio -- so the terminal itself needs
just enough file manipulation for a user to create and edit content to
stage. These builtins are deliberately minimal (no globbing, no flags
besides what's listed) and every path is sandboxed to REPO_ROOT using
the same resolve()/relative_to() safety check `index.stage_file`
already uses, so a command can never read or write outside the
repository.

`clear`, `history`, and `help` are intentionally NOT here: they carry
no repository state and are handled entirely on the frontend (see
frontend/src/features/terminal/useTerminal.ts) since there is nothing
for a StudioResponse to meaningfully report for them.
"""

from dataclasses import dataclass
from pathlib import Path

from snapshot.index import IGNORED_DIR_NAMES


@dataclass
class BuiltinResult:
    stdout_lines: list[str]
    stderr_lines: list[str]
    exit_code: int


def resolve_in_repo(repo_root: Path, raw_path: str) -> Path:
    """Resolve a user-supplied path, raising ValueError if it would escape the repo root."""
    candidate = (repo_root / raw_path).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"'{raw_path}' is outside the repository") from exc
    return candidate


def run_echo(repo_root: Path, args: list[str]) -> BuiltinResult:
    content_tokens, redirect_op, target = _split_redirection(args)
    text = " ".join(content_tokens)

    if target is None:
        return BuiltinResult(stdout_lines=[text], stderr_lines=[], exit_code=0)

    try:
        file_path = resolve_in_repo(repo_root, target)
    except ValueError as exc:
        return BuiltinResult(stdout_lines=[], stderr_lines=[f"echo: {exc}"], exit_code=1)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    if redirect_op == ">>" and file_path.exists():
        with file_path.open("a") as f:
            f.write(text + "\n")
    else:
        file_path.write_text(text + "\n")
    return BuiltinResult(stdout_lines=[], stderr_lines=[], exit_code=0)


def run_cat(repo_root: Path, args: list[str]) -> BuiltinResult:
    if not args:
        return BuiltinResult(stdout_lines=[], stderr_lines=["cat: missing file operand"], exit_code=1)

    stdout: list[str] = []
    stderr: list[str] = []
    for raw_path in args:
        try:
            file_path = resolve_in_repo(repo_root, raw_path)
        except ValueError as exc:
            stderr.append(f"cat: {exc}")
            continue
        if not file_path.is_file():
            stderr.append(f"cat: {raw_path}: no such file")
            continue
        try:
            stdout.extend(file_path.read_text().splitlines())
        except UnicodeDecodeError:
            stderr.append(f"cat: {raw_path}: binary file")
    exit_code = 1 if stderr and not stdout else 0
    return BuiltinResult(stdout_lines=stdout, stderr_lines=stderr, exit_code=exit_code)


def run_ls(repo_root: Path, args: list[str]) -> BuiltinResult:
    target_raw = args[0] if args else "."
    try:
        dir_path = resolve_in_repo(repo_root, target_raw)
    except ValueError as exc:
        return BuiltinResult(stdout_lines=[], stderr_lines=[f"ls: {exc}"], exit_code=1)

    if not dir_path.is_dir():
        return BuiltinResult(stdout_lines=[], stderr_lines=[f"ls: {target_raw}: not a directory"], exit_code=1)

    names = sorted(
        p.name + ("/" if p.is_dir() else "")
        for p in dir_path.iterdir()
        if p.name not in IGNORED_DIR_NAMES
    )
    return BuiltinResult(stdout_lines=names, stderr_lines=[], exit_code=0)


def run_mkdir(repo_root: Path, args: list[str]) -> BuiltinResult:
    if not args:
        return BuiltinResult(stdout_lines=[], stderr_lines=["mkdir: missing operand"], exit_code=1)
    stderr: list[str] = []
    for raw_path in args:
        try:
            dir_path = resolve_in_repo(repo_root, raw_path)
        except ValueError as exc:
            stderr.append(f"mkdir: {exc}")
            continue
        dir_path.mkdir(parents=True, exist_ok=True)
    return BuiltinResult(stdout_lines=[], stderr_lines=stderr, exit_code=1 if stderr else 0)


def run_rm(repo_root: Path, args: list[str]) -> BuiltinResult:
    if not args:
        return BuiltinResult(stdout_lines=[], stderr_lines=["rm: missing operand"], exit_code=1)
    stderr: list[str] = []
    for raw_path in args:
        try:
            file_path = resolve_in_repo(repo_root, raw_path)
        except ValueError as exc:
            stderr.append(f"rm: {exc}")
            continue
        if file_path.is_dir():
            stderr.append(f"rm: {raw_path}: is a directory")
        elif not file_path.exists():
            stderr.append(f"rm: {raw_path}: no such file")
        else:
            file_path.unlink()
    return BuiltinResult(stdout_lines=[], stderr_lines=stderr, exit_code=1 if stderr else 0)


def run_touch(repo_root: Path, args: list[str]) -> BuiltinResult:
    if not args:
        return BuiltinResult(stdout_lines=[], stderr_lines=["touch: missing file operand"], exit_code=1)
    stderr: list[str] = []
    for raw_path in args:
        try:
            file_path = resolve_in_repo(repo_root, raw_path)
        except ValueError as exc:
            stderr.append(f"touch: {exc}")
            continue
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch(exist_ok=True)
    return BuiltinResult(stdout_lines=[], stderr_lines=stderr, exit_code=1 if stderr else 0)


def _split_redirection(args: list[str]) -> tuple[list[str], str | None, str | None]:
    for op in (">>", ">"):
        if op in args:
            idx = args.index(op)
            target = args[idx + 1] if idx + 1 < len(args) else None
            return args[:idx], op, target
    return args, None, None
