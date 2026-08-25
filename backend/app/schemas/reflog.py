"""The Reflog DTO: every commit HEAD has pointed at, newest first, with
whether each is still reachable from any current branch tip -- the
signal the Studio's Reflog view uses to mark an entry "unreachable."
"""

from pydantic import BaseModel


class ReflogEntryDTO(BaseModel):
    index: int  # HEAD@{n}, 0 = most recent
    old_oid: str | None  # None if this was the very first entry ever recorded
    new_oid: str
    short_new_oid: str
    timestamp: int
    message: str
    is_reachable: bool


class ReflogResponse(BaseModel):
    entries: list[ReflogEntryDTO]
