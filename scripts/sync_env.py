"""Merge local sync_env.yaml into GCS env.yaml files for each service.

For each service, downloads the existing env.yaml from GCS, merges in
values from the local sync_env.yaml (overwriting matching keys), and
uploads the result back.

Usage:
    poetry run python scripts/sync_env.py -e test              # Update all services in test
    poetry run python scripts/sync_env.py -e test -s wearables # Update only wearables in test
"""

import argparse
import io
import sys
from pathlib import Path

import yaml
from google.cloud import storage
from google.cloud.exceptions import NotFound

_BUCKET_MAP = {
    "test": "eshop-test-config",
    "prod": "eshop-prod-config",
}
_BASE_PATH = "services"
_SYNC_ENV_PATH = Path(__file__).parent / "sync_env.yaml"

_ALL_SERVICES = ["hello-world", "api-gateway", "wearables"]


def _read_sync_env() -> dict[str, str]:
    if not _SYNC_ENV_PATH.exists():
        print(f"Error: {_SYNC_ENV_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(stream=_SYNC_ENV_PATH.read_text()) or {}


def _download_env(client: storage.Client, bucket_name: str, service_name: str) -> dict[str, str]:
    bucket = client.bucket(bucket_name=bucket_name)
    blob_path = f"{_BASE_PATH}/{service_name}/env.yaml"
    blob = bucket.blob(blob_name=blob_path)
    try:
        content = blob.download_as_text()
    except NotFound:
        return {}
    return yaml.safe_load(stream=content) or {}


def _upload_env(client: storage.Client, bucket_name: str, service_name: str, env: dict[str, str]) -> str:
    bucket = client.bucket(bucket_name=bucket_name)
    blob_path = f"{_BASE_PATH}/{service_name}/env.yaml"
    blob = bucket.blob(blob_name=blob_path)
    content = yaml.dump(data=env, default_flow_style=False, sort_keys=True)
    blob.upload_from_file(file_obj=io.BytesIO(content.encode()), content_type="application/x-yaml")
    return f"gs://{bucket_name}/{blob_path}"


def _sync(services: list[str], bucket_name: str) -> None:
    updates = _read_sync_env()
    if not updates:
        print("sync_env.yaml is empty, nothing to do.")
        return

    client = storage.Client()

    for service_name in services:
        existing = _download_env(client=client, bucket_name=bucket_name, service_name=service_name)
        existing.update(updates)
        gcs_path = _upload_env(client=client, bucket_name=bucket_name, service_name=service_name, env=existing)
        print(f"Uploaded {gcs_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge sync_env.yaml into GCS env.yaml files.")
    parser.add_argument("-e", "--env", choices=list(_BUCKET_MAP.keys()), required=True, help="Target environment.")
    parser.add_argument("-s", "--service", choices=_ALL_SERVICES, help="Update a single service.")
    args = parser.parse_args()

    services = [args.service] if args.service else _ALL_SERVICES
    _sync(services=services, bucket_name=_BUCKET_MAP[args.env])


if __name__ == "__main__":
    main()
