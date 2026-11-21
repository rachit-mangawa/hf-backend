"""Storage utility for syncing subproject databases and artifacts to/from buckets."""

import logging
import os
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hf-backend.storage")


def get_storage_info() -> dict[str, Any]:
    """Returns storage configuration metadata without exposing secret keys."""
    bucket_name = (
        os.getenv("STORAGE_BUCKET_NAME")
        or os.getenv("BUCKET_NAME")
        or os.getenv("HF_BUCKET_NAME")
        or ""
    ).strip()
    endpoint_url = (
        os.getenv("STORAGE_ENDPOINT_URL")
        or os.getenv("S3_ENDPOINT_URL")
        or ""
    ).strip()
    region = (
        os.getenv("STORAGE_REGION")
        or os.getenv("AWS_REGION")
        or ""
    ).strip()

    return {
        "configured": bool(bucket_name),
        "bucket_name": bucket_name or None,
        "endpoint_url": endpoint_url or None,
        "region": region or None,
    }


def download_from_bucket(remote_path: str, local_path: str | Path) -> bool:
    """Downloads a file or database from the configured storage bucket."""
    cfg = get_storage_info()
    bucket = cfg["bucket_name"]
    if not bucket:
        logger.warning(f"Storage bucket not configured. Skipping download of '{remote_path}'.")
        return False

    dest = Path(local_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Hugging Face Storage Bucket (via huggingface_hub)
        if bucket.startswith("hf://") or "/" in bucket:
            from huggingface_hub import hffs
            clean_bucket = bucket.replace("hf://buckets/", "").replace("hf://", "")
            remote_uri = f"buckets/{clean_bucket}/{remote_path.lstrip('/')}"
            logger.info(f"Downloading {remote_uri} -> {dest} via HF Storage...")
            with hffs.open(remote_uri, "rb") as f_in, open(dest, "wb") as f_out:
                f_out.write(f_in.read())
            logger.info(f"Successfully downloaded {remote_path} from HF bucket.")
            return True

        # 2. S3-compatible bucket
        endpoint = cfg["endpoint_url"]
        region = cfg["region"] or "us-east-1"
        access_key = os.getenv("STORAGE_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("STORAGE_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")

        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        s3.download_file(bucket, remote_path, str(dest))
        logger.info(f"Successfully downloaded {remote_path} from S3 bucket {bucket}.")
        return True
    except Exception as e:
        logger.error(f"Failed to download {remote_path} from bucket: {e}")
        return False


def upload_to_bucket(local_path: str | Path, remote_path: str) -> bool:
    """Uploads a file or database to the configured storage bucket."""
    cfg = get_storage_info()
    bucket = cfg["bucket_name"]
    if not bucket:
        logger.warning(f"Storage bucket not configured. Skipping upload of '{local_path}'.")
        return False

    src = Path(local_path)
    if not src.exists():
        logger.warning(f"Local file '{src}' does not exist. Skipping upload.")
        return False

    try:
        # 1. Hugging Face Storage Bucket
        if bucket.startswith("hf://") or "/" in bucket:
            from huggingface_hub import hffs
            clean_bucket = bucket.replace("hf://buckets/", "").replace("hf://", "")
            remote_uri = f"buckets/{clean_bucket}/{remote_path.lstrip('/')}"
            logger.info(f"Uploading {src} -> {remote_uri} via HF Storage...")
            with open(src, "rb") as f_in, hffs.open(remote_uri, "wb") as f_out:
                f_out.write(f_in.read())
            logger.info(f"Successfully uploaded {local_path} to HF bucket.")
            return True

        # 2. S3-compatible bucket
        endpoint = cfg["endpoint_url"]
        region = cfg["region"] or "us-east-1"
        access_key = os.getenv("STORAGE_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("STORAGE_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")

        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        s3.upload_file(str(src), bucket, remote_path)
        logger.info(f"Successfully uploaded {local_path} to S3 bucket {bucket}.")
        return True
    except Exception as e:
        logger.error(f"Failed to upload {local_path} to bucket: {e}")
        return False
