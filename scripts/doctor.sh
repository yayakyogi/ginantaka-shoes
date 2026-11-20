#!/usr/bin/env bash
# Checks the tools listed in PLAN.md (Phase 0 human prerequisites).
set -u

status=0

check() {
  local name=$1
  shift
  if command -v "$name" >/dev/null 2>&1; then
    printf 'ok       %-8s %s\n' "$name" "$("$@" 2>&1 | head -n 1)"
  else
    printf 'MISSING  %s\n' "$name"
    status=1
  fi
}

check git git --version
check uv uv --version
check bun bun --version
check node node --version
check task task --version
check docker docker --version

if command -v node >/dev/null 2>&1; then
  major=$(node -p 'process.versions.node.split(".")[0]')
  if [ "$major" -lt 20 ]; then
    echo "node must be >= 20 (found $major)"
    status=1
  fi
fi

if command -v docker >/dev/null 2>&1 && ! docker info >/dev/null 2>&1; then
  echo "docker is installed but not running: start Docker Desktop"
  status=1
fi

exit $status
