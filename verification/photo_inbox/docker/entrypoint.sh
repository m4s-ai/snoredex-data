#!/bin/sh
# Start the inbox (default) or the sync loop that keeps the mounted checkouts current.
set -eu

if [ "${1:-inbox}" = "sync" ]; then
  # fast-forward only: the checkouts are read here, never edited; a failed pull waits for the next round
  while true; do
    for checkout in /checkouts/snoredex-data /checkouts/snoredex-photos; do
      git -C "$checkout" pull --ff-only --quiet || echo "sync: pull failed for $checkout" >&2
    done
    sleep "${SYNC_SECONDS:-600}"
  done
fi

set -- --data-dir /data --host 0.0.0.0 --port "${PORT:-8765}" \
  --repo /checkouts/snoredex-data --photos /checkouts/snoredex-photos
if [ -n "${UPLOADER_URL:-}" ]; then
  # the key itself stays in the environment (UPLOADER_KEY); it never appears on the command line
  set -- "$@" --uploader "$UPLOADER_URL"
fi
exec python verification/photo_inbox/app.py "$@"
