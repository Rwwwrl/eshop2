#!/usr/bin/env bash
set -euo pipefail

gcloud container clusters delete eshop-cluster \
    --region europe-west3 \
    --project eshop-test-485206 \
    --quiet
