# coding: utf-8
import logging
import os
import json

from minio import Minio
from minio.error import ResponseError, NoSuchBucket

from documentstore_migracao.utils import files, xml
from documentstore_migracao import config

logger = logging.getLogger(__name__)


class MinioStorage:
    def __init__(
        self, minio_host, minio_access_key, minio_secret_key, minio_secure=True
    ):

        self.bucket_name = "documentstore"
        self.POLICY_READ_ONLY = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_name}"],
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                },
            ],
        }
        self.minio_host = minio_host
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_secure = minio_secure
        self._client_instance = None

    @property
    def _client(self):
        """Posterga a instanciação de `pymongo.MongoClient` até o seu primeiro
        uso.
        """
        if not self._client_instance:
            # Initialize minioClient with an endpoint and access/secret keys.
            self._client_instance = Minio(
                self.minio_host,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=self.minio_secure,
            )
            logger.debug(
                "new Minio client created: <%s at %s>",
                repr(self._client_instance),
                id(self._client_instance),
            )

        logger.debug(
            "using Minio client: <%s at %s>",
            repr(self._client_instance),
            id(self._client_instance),
        )
        return self._client_instance

    def _create_bucket(self):
        # Make a bucket with the make_bucket API call.
        try:
            self._client.make_bucket(
                self.bucket_name, location=config.get("SCIELO_COLLECTION")
            )
            self._set_public_bucket()
        except ResponseError as err:
            raise

    def _set_public_bucket(self):
        self._client.set_bucket_policy(
            self.bucket_name, json.dumps(self.POLICY_READ_ONLY)
        )

    def _generator_media_path(self, file_path, prefix):
        """
        2 niveis de Pastas onde :
            * o primeiro representando o periódico por meio do ISSN+Acrônimo
            * o segundo o scielo-id do documento no seu idioma original.
            Var: Prefix
        O nome do arquivo sera alterado para soma SHA-1, para evitar duplicatas e conflitos em nomes.
        """
        n_filename = files.calcule_sha1(file_path)
        _, file_extension = os.path.splitext(os.path.basename(file_path))

        return f"{prefix}/{n_filename}{file_extension}"

    def get_urls(self, media_path: str) -> str:

        url = self._client.presigned_get_object(self.bucket_name, media_path)
        return url.split("?")[0]

    def register(self, file_path, prefix="") -> str:
        media_path = self._generator_media_path(file_path, prefix)
        metadata = {"origin_name": os.path.basename(file_path)}

        try:
            self._client.fput_object(
                self.bucket_name, media_path, file_path=file_path, metadata=metadata
            )

        except NoSuchBucket as err:
            logger.info(err)
            self._create_bucket()
            return self.register(file_path)

        except ResponseError as err:
            print(err)

        return self.get_urls(media_path)

    def remove(self, media_path: str) -> None:
        # Remove an object.
        try:
            self._client.remove_object(self.bucket_name, media_path)
        except ResponseError as err:
            print(err)
