#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <image>" >&2
  exit 2
fi

trivy image \
  --scanners vuln \
  --severity CRITICAL \
  --ignore-unfixed=false \
  --exit-code 1 \
  "$1"

