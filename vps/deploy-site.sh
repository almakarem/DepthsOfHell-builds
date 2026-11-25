#!/usr/bin/env bash
# Puts the website from this repo's branch onto the VPS.
#   sudo bash deploy-site.sh   (run from a clone of this branch)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT=/var/www/depthsofhell
mkdir -p "$ROOT/site"
rsync -a --delete "$HERE/site/" "$ROOT/site/"
chmod -R a+rX "$ROOT/site"
echo "Site deployed to $ROOT/site"
