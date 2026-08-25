"""Repository Status DTO -- a read-only summary of HEAD, current branch,
current commit, working directory, and index state."""

from pydantic import BaseModel


class RepositoryStatus(BaseModel):
    initialized: bool
    head_detached: bool
    current_branch: str | None
    current_commit_oid: str | None
    working_directory_clean: bool
    staged_paths: list[str]
    unstaged_paths: list[str]
    untracked_paths: list[str]
    conflicted_paths: list[str]
