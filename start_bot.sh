#!/bin/bash

BASE_DIR="/home/felix/automation-check/dekallm-litellm"
ENV_FILE="$BASE_DIR/.env"
PYTHON_SCRIPT="$BASE_DIR/bot_kube.py"

echo "Checking .env file..."
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

echo "Environment variables successfully loaded."
echo "Starting KubeOps Slack Bot..."

/usr/bin/python3 "$PYTHON_SCRIPT"