import os
import aioboto3


from typing import AsyncGenerator, AsyncIterator, BinaryIO, Iterator, Tuple, Optional

from open_webui.constants import ERROR_MESSAGES
from open_webui.config import (
    S3_BUCKET_PREFIX,
    S3_LOCAL_CACHE_DIR,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_REGION_NAME,
    S3_ENDPOINT_URL,
    UPLOAD_DIR,
)
from mypy_boto3_s3.client import S3Client
from smart_open import open
import boto3
from typing import BinaryIO, Tuple, Optional


from openwebui.backend.open_webui.storage.base_storage_provider import LocalCachedFile, StorageProvider

class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.session = aioboto3.Session()
        # self.s3_client: S3Client = 
        self.bucket_name: Optional[str] = S3_BUCKET_NAME
        self.bucket_prefix: Optional[str] = S3_BUCKET_PREFIX

    def get_client(self):
        return self.session.client(
            "s3",
            region_name=S3_REGION_NAME,
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        )

    async def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to S3."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        try:
            await self.get_client().put_object(Bucket=self.bucket_name, Key=f"{self.bucket_prefix}/{filename}", Body=contents)
            return contents, f"s3://{self.bucket_name}/{self.bucket_prefix}/{filename}"
        except Exception as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    async def get_file(self, file_path: str) :
        """Downloads a file from S3 and returns the local file path."""
        try:
            bucket_name, key = file_path.split("//")[1].split("/", 1)
            # local_file_path = f"{S3_LOCAL_CACHE_DIR}/{key}"
            # os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            response = await self.get_client().get_object(Bucket=bucket_name, Key=key)
            return response.get("Body").iter_chunks()
        except Exception as e:
            raise RuntimeError(f"Error downloading file {file_path} from S3: {e}")
        
    async def as_local_file(self, file_path: str) -> LocalCachedFile:
        try:
            bucket_name, key = file_path.split("//")[1].split("/", 1)
            local_file_path = f"{S3_LOCAL_CACHE_DIR}/{key}"
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            await self.get_client().download_file(bucket_name, key, local_file_path)
            print(f"download s3 file to {local_file_path}")
            return LocalCachedFile(local_file_path)
        except Exception as e:
            raise RuntimeError(f"Error downloading file {file_path} from S3: {e}")

    async def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""
        try:
            await self.get_client().delete_object(Bucket=self.bucket_name, Key=filename)
        except Exception as e:
            raise RuntimeError(f"Error deleting file {filename} from S3: {e}")

    async def delete_all_files(self) -> None:
        """Deletes all files from S3."""
        try:
            response = await self.get_client().list_objects_v2(Bucket=self.bucket_name, Prefix=self.bucket_prefix)
            if "Contents" in response:
                for content in response["Contents"]:
                    await self.get_client().delete_object(
                        Bucket=self.bucket_name, Key=content["Key"]
                    )
        except Exception as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")