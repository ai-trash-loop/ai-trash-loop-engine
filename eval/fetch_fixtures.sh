#!/usr/bin/env bash
# Clone the evaluation fixtures from their upstream projects at the pinned commits.
# Only `git clone`/`git checkout` run; nothing from these repos is built or executed.
# Usage: eval/fetch_fixtures.sh [target_dir]   (default: ./fixtures)
set -euo pipefail
dest="${1:-fixtures}"
mkdir -p "$dest"

fetch() { # name url sha
  local name="$1" url="$2" sha="$3"
  if [ -d "$dest/$name/.git" ]; then echo "skip $name (exists)"; return; fi
  git clone --quiet "$url" "$dest/$name"
  git -C "$dest/$name" checkout --quiet "$sha"
  echo "ok   $name @ ${sha:0:10}"
}

fetch agents-adrs               https://github.com/gmoigneu/agents-adrs.git                        a36a10638c8dab2175ad2cc9e0affd32dae7b4c7
fetch just-dummies              https://github.com/Reefact/just-dummies.git                        522a73de07123f04beae1382065947230eefd2ec
fetch spring-petclinic-modulith https://github.com/spring-petclinic/spring-petclinic-modulith.git  58c3310e36c7d827959df6af4d64bdeb8d81f1ea
