"""Upload local env.yaml files to GCS, replacing remote copies.

The local directory structure mirrors the GCS bucket layout:

    scripts/sync_env/{env}/
        api-gateway/env.yaml
        hello-world/env.yaml
        wearables/env.yaml

Each env.yaml is uploaded as-is to gs://{bucket}/services/{service}/env.yaml.

Usage:
    poetry run python scripts/sync_env/sync_env.py --env test-eu
"""

import argparse
import io
from pathlib import Path

from google.cloud import storage

_BUCKET_MAP = {
    "test-eu": "eshop-test-config",
}
_GCS_BASE_PATH = "services"
_ENVS_DIR = Path(__file__).parent


def _discover_services(env_dir: Path) -> list[Path]:
    return sorted(p.parent for p in env_dir.glob("*/env.yaml"))


def _upload(client: storage.Client, bucket_name: str, service_name: str, content: str) -> str:
    bucket = client.bucket(bucket_name=bucket_name)
    blob_path = f"{_GCS_BASE_PATH}/{service_name}/env.yaml"
    blob = bucket.blob(blob_name=blob_path)
    blob.upload_from_file(file_obj=io.BytesIO(content.encode()), content_type="application/x-yaml")
    return f"gs://{bucket_name}/{blob_path}"


def _sync(env: str) -> None:
    env_dir = _ENVS_DIR / env
    bucket_name = _BUCKET_MAP[env]
    client = storage.Client()

    for service_dir in _discover_services(env_dir=env_dir):
        content = (service_dir / "env.yaml").read_text()
        gcs_path = _upload(
            client=client,
            bucket_name=bucket_name,
            service_name=service_dir.name,
            content=content,
        )
        print(f"Uploaded {gcs_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload local env.yaml files to GCS.")
    parser.add_argument(
        "--env",
        choices=list(_BUCKET_MAP.keys()),
        required=True,
        help="Target environment.",
    )
    args = parser.parse_args()
    _sync(env=args.env)


if __name__ == "__main__":
    main()
