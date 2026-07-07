from typing import BinaryIO

from services.storage_provider.base import StorageProvider
from params import S3_BUCKET, S3_ENDPOINT_URL, S3_REGION, S3_ACCESS_KEY, S3_SECRET_KEY


class S3Provider(StorageProvider):
    """Stockage sur un service compatible S3 (AWS S3, MinIO, Scaleway...), via boto3.
    ⚠️ Non testé dans cet environnement de développement (aucun bucket/identifiants S3
    réels disponibles) — implémenté selon l'API standard boto3 `Object.put/get/delete`,
    à valider avec un vrai bucket avant mise en production.

    Activation : définir STORAGE_PROVIDER=s3 et les variables S3_* (voir params.py),
    puis installer la dépendance optionnelle `boto3`. Tant que ce n'est pas fait,
    storage_provider/__init__.py continue de servir LocalDiskProvider."""

    nom = "s3"

    def __init__(self):
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError(
                "Le provider de stockage 's3' nécessite le paquet 'boto3' (pip install boto3)"
            ) from e

        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET doit être défini pour utiliser le provider de stockage 's3'")

        self.bucket = S3_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL or None,
            region_name=S3_REGION or None,
            aws_access_key_id=S3_ACCESS_KEY or None,
            aws_secret_access_key=S3_SECRET_KEY or None,
        )

    def upload(self, cle: str, fileobj: BinaryIO) -> int:
        self._client.upload_fileobj(fileobj, self.bucket, cle)
        head = self._client.head_object(Bucket=self.bucket, Key=cle)
        return head["ContentLength"]

    def download(self, cle: str) -> BinaryIO:
        import io
        buffer = io.BytesIO()
        self._client.download_fileobj(self.bucket, cle, buffer)
        buffer.seek(0)
        return buffer

    def delete(self, cle: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=cle)

    def exists(self, cle: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self._client.head_object(Bucket=self.bucket, Key=cle)
            return True
        except ClientError:
            return False
