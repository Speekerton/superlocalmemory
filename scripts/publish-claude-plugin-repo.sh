#!/usr/bin/env bash
# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
#
# publish-claude-plugin-repo.sh — copy the built Claude Code plugin (plugin/)
# to the root of github.com/qualixar/superlocalmemory-plugin, commit, tag.
#
# USAGE (from the repository root, after scripts/build-all-plugins.mjs):
#   scripts/publish-claude-plugin-repo.sh            # version from plugin.json
#
# WHY
#   Anthropic's plugin directory checks a plugin more strictly when it sits in
#   a subfolder of a larger repository: every .gitattributes above it counts
#   (this repository's Git LFS and line-ending rules stop validation), and a
#   launch command using any variable but ${CLAUDE_PLUGIN_ROOT} blocks instead
#   of going to a reviewer. The directory tracks this dedicated repository,
#   which holds exactly the plugin folder of each release and nothing else.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/plugin"
REPO_URL="${SLM_PLUGIN_REPO_URL:-https://github.com/qualixar/superlocalmemory-plugin.git}"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$SRC/.claude-plugin/plugin.json")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

git clone --quiet "$REPO_URL" "$WORK/repo"
# Replace everything but .git with the plugin folder, byte for byte.
find "$WORK/repo" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$SRC/." "$WORK/repo/"

cd "$WORK/repo"
git checkout --quiet -B main  # an empty repository has no branch yet
git add -A
if git diff --cached --quiet; then
  echo "superlocalmemory-plugin already matches $VERSION."
  exit 0
fi
git commit --quiet -m "SuperLocalMemory plugin $VERSION

Built from github.com/qualixar/superlocalmemory (plugin/) at $(git -C "$ROOT" rev-parse --short HEAD)."
git tag -a "v$VERSION" -m "SuperLocalMemory plugin $VERSION"
git push --quiet origin main
git push --quiet origin "v$VERSION"
echo "Published superlocalmemory-plugin $VERSION ($(git rev-parse --short HEAD))."
