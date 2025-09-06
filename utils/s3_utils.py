"""
S3 utility layer for the YOLO service.

Env vars (via .env or environment):
  - AWS_REGION   e.g., "us-west-1"
  - BUCKET_NAME  default bucket name, e.g., "akheel-yolo-images"
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
"""

import os
import mimetypes
import tempfile
from typing import Optional, BinaryIO
from io import BytesIO

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

AWS_REGION: Optional[str] = os.getenv("AWS_REGION") or "us-west-1"
DEFAULT_BUCKET: Optional[str] = os.getenv("BUCKET_NAME") or "akheel-yolo-images"

# Initialize S3 client
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)


def upload_file_to_s3(file_obj: BinaryIO, bucket: str, key: str, content_type: Optional[str] = None) -> str:
    """
    Upload a file object to S3.
    
    Args:
        file_obj: File-like object to upload
        bucket: S3 bucket name
        key: S3 object key (path)
        content_type: MIME type of the file
        
    Returns:
        S3 URL of the uploaded file
    """
    try:
        # Determine content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(key)
            if not content_type:
                content_type = 'application/octet-stream'
        
        # Upload file
        s3_client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={'ContentType': content_type}
        )
        
        # Return S3 URL
        return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{key}"
        
    except (BotoCoreError, ClientError) as e:
        raise Exception(f"Failed to upload file to S3: {str(e)}")


def download_file_from_s3(bucket: str, key: str) -> BytesIO:
    """
    Download a file from S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path)
        
    Returns:
        BytesIO object containing the file data
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return BytesIO(response['Body'].read())
        
    except (BotoCoreError, ClientError) as e:
        raise Exception(f"Failed to download file from S3: {str(e)}")


def upload_image_to_s3(image_data: bytes, folder: str, filename: str, bucket: str = DEFAULT_BUCKET) -> str:
    """
    Upload image data to S3.
    
    Args:
        image_data: Image data as bytes
        folder: S3 folder (e.g., 'original' or 'predicted')
        filename: Name of the file
        bucket: S3 bucket name
        
    Returns:
        S3 URL of the uploaded image
    """
    key = f"{folder}/{filename}"
    content_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'
    
    file_obj = BytesIO(image_data)
    return upload_file_to_s3(file_obj, bucket, key, content_type)


def download_image_from_s3(s3_url: str, bucket: str = DEFAULT_BUCKET) -> BytesIO:
    """
    Download image from S3 using S3 URL.
    
    Args:
        s3_url: Full S3 URL of the image
        bucket: S3 bucket name
        
    Returns:
        BytesIO object containing the image data
    """
    # Extract key from S3 URL
    # URL format: https://bucket.s3.region.amazonaws.com/key
    key = s3_url.split(f"{bucket}.s3.{AWS_REGION}.amazonaws.com/")[-1]
    return download_file_from_s3(bucket, key)


def delete_file_from_s3(s3_url: str, bucket: str = DEFAULT_BUCKET) -> bool:
    """
    Delete a file from S3 using S3 URL.
    
    Args:
        s3_url: Full S3 URL of the file
        bucket: S3 bucket name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract key from S3 URL
        key = s3_url.split(f"{bucket}.s3.{AWS_REGION}.amazonaws.com/")[-1]
        s3_client.delete_object(Bucket=bucket, Key=key)
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"Failed to delete file from S3: {str(e)}")
        return False


def get_s3_url(bucket: str, key: str) -> str:
    """
    Generate S3 URL from bucket and key.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Full S3 URL
    """
    return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{key}"
