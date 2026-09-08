"""Select the retained runs needed for an incremental projection.

Run IDs are the acquisition order.  A projection compares one run with its direct predecessor;
older runs do not change that result.  The full-refresh switch remains available for the deeper
historical validation lane.
"""

from __future__ import annotations

from collections.abc import Sequence


def select_projection_run_ids(
    run_ids: Sequence[str], latest_run_id: str, full_refresh: bool = False
) -> list[str]:
    """Return the run IDs required to build *latest_run_id*.

    The caller must provide IDs in acquisition order and the selected latest ID must be present.
    Incremental mode retains the immediate predecessor so the generated diff is unchanged; full
    refresh deliberately returns every retained ID for historical validation.
    """
    ordered = list(run_ids)
    try:
        latest_index = ordered.index(latest_run_id)
    except ValueError as error:
        raise ValueError(f"latest run is not retained: {latest_run_id}") from error
    if full_refresh:
        return ordered
    return ordered[max(0, latest_index - 1): latest_index + 1]
