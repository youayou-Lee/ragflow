#!/bin/bash

# Load environment variables from docker/.env
if [ -f docker/.env ]; then
    echo "Loading environment variables from docker/.env"
    set -a
    source docker/.env
    set +a
fi

unset ALL_PROXY && unset all_proxy
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh
