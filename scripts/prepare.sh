#!/bin/bash
SCRIPT_PATH="$(dirname -- "${BASH_SOURCE[0]}")"
SCRIPT_PATH="$(cd -- "$SCRIPT_PATH" && pwd)"
if [[ -z $SCRIPT_PATH ]]; then
    exit 1
fi
ROOT_PATH=$(realpath "${SCRIPT_PATH}/..")

echo "Running from $ROOT_PATH"

mkdir -p _site/img
rsync -av ../img/ _site/img
