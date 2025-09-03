import boto3
from botocore.exceptions import BotoCoreError, ClientError

def get_s3_client():
    """Return a boto3 S3 client."""
    return boto3.client("s3")

def s3_public_url(bucket: str, key: str) -> str:
    """Build a public S3 URL. Adjust if you use presigned URLs instead."""
    return f"https://{bucket}.s3.amazonaws.com/{key}"

def s3_download_file(bucket: str, key: str, dest_path: str):
    """Download a file from S3 to local path."""
    try:
        get_s3_client().download_file(bucket, key, dest_path)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Failed to download from S3: {e}")

def s3_upload_file(bucket: str, key: str, file_path: str):
    """Upload a local file to S3."""
    try:
        get_s3_client().upload_file(file_path, bucket, key)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Failed to upload to S3: {e}")

def s3_ensure_folders(bucket: str):
    """Optionally create folder markers in S3."""
    s3 = get_s3_client()
    try:
        s3.put_object(Bucket=bucket, Key="original/")
        s3.put_object(Bucket=bucket, Key="predicted/")
    except (BotoCoreError, ClientError):
        pass  # Not fatal
