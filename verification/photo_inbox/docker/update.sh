#!/bin/sh
# Update the inbox on the Homelab (#666): pull this checkout, rebuild the image with the commit it is
# built from, and print that commit. The inbox's version line must then show the same one.
set -eu
cd "$(dirname "$0")"
git pull --ff-only
GIT_COMMIT=$(git rev-parse HEAD)
BUILT_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
export GIT_COMMIT BUILT_AT
docker compose up -d --build
echo "inbox built from $(git rev-parse --short HEAD) at $BUILT_AT: check the version line at the page's foot"
