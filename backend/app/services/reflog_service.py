"""Builds the Reflog DTO. Read-only, same as graph_builder.py: only
reads through the engine's `reflog` module and the existing
`graph_builder.build_graph` (whose `.commits` list *is* "every commit
reachable from a branch tip or detached HEAD right now" -- exactly the
reachability answer this needs, so no new walk is written here).
"""

from pathlib import Path

from snapshot import reflog as reflog_mod

from app.schemas.reflog import ReflogEntryDTO, ReflogResponse
from app.services import graph_builder


def build_reflog(snapshot_dir: Path, objects_dir: Path) -> ReflogResponse:
    entries = list(reversed(reflog_mod.read_entries(snapshot_dir)))
    graph = graph_builder.build_graph(snapshot_dir, objects_dir)
    reachable_oids = {c.oid for c in graph.commits}

    dtos = [
        ReflogEntryDTO(
            index=i,
            old_oid=None if entry.old_oid == reflog_mod.ZERO_OID else entry.old_oid,
            new_oid=entry.new_oid,
            short_new_oid=entry.new_oid[:7],
            timestamp=entry.timestamp,
            message=entry.message,
            is_reachable=entry.new_oid in reachable_oids,
        )
        for i, entry in enumerate(entries)
    ]
    return ReflogResponse(entries=dtos)
