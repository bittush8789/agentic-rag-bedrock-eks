import os
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logging import logger


class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        self.bucket = settings.S3_BUCKET_NAME
        self.local_dir = settings.LOCAL_STORAGE_DIR

        self._s3_client = None
        if self.backend == "s3":
            try:
                self._s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
            except Exception as e:
                logger.warning(f"Could not connect to S3: {e}. Falling back to local storage.")
                self.backend = "local"

        if self.backend == "local":
            os.makedirs(self.local_dir, exist_ok=True)

    async def save_file(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Saves file bytes to configured storage backend."""
        if self.backend == "s3" and self._s3_client:
            try:
                self._s3_client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type
                )
                return f"s3://{self.bucket}/{key}"
            except ClientError as e:
                logger.error(f"S3 PutObject error: {e}")
                raise

        # Local storage fallback
        file_path = os.path.join(self.local_dir, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    async def get_file(self, key: str) -> bytes:
        """Retrieves file bytes from configured storage backend."""
        if self.backend == "s3" and self._s3_client:
            try:
                response = self._s3_client.get_object(Bucket=self.bucket, Key=key)
                return response["Body"].read()
            except ClientError as e:
                logger.error(f"S3 GetObject error: {e}")
                raise

        file_path = os.path.join(self.local_dir, key)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Storage file not found: {key}")
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, key: str) -> None:
        """Deletes file from storage backend."""
        if self.backend == "s3" and self._s3_client:
            try:
                self._s3_client.delete_object(Bucket=self.bucket, Key=key)
                return
            except ClientError as e:
                logger.warning(f"Failed to delete S3 object {key}: {e}")
                return

        file_path = os.path.join(self.local_dir, key)
        if os.path.exists(file_path):
            os.remove(file_path)


storage_service = StorageService()
