# from __future__ import annotations
# import boto3
# from botocore.exceptions import ClientError
# from typing import Optional
# import os

# class S3Store:
#     """
#     Store and retrieve files from AWS S3.
#     Requires AWS credentials in env or ~/.aws/credentials.
#     """

#     def __init__(self, bucket_name: str, region_name: Optional[str] = None):
#         self.bucket = bucket_name
#         self.s3 = boto3.client("s3", region_name=region_name)

#     def save(self, file_bytes: bytes, key: str, public: bool = False) -> str:
#         """Upload bytes to S3 and return the object URL."""
#         extra_args = {}
#         if public:
#             extra_args["ACL"] = "public-read"

#         self.s3.put_object(
#             Bucket=self.bucket,
#             Key=key,
#             Body=file_bytes,
#             **extra_args
#         )

#         location = self.s3.get_bucket_location(Bucket=self.bucket)["LocationConstraint"]
#         if location:
#             url = f"https://{self.bucket}.s3.{location}.amazonaws.com/{key}"
#         else:
#             url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
#         return url

#     def load(self, key: str) -> bytes:
#         """Download object from S3."""
#         try:
#             resp = self.s3.get_object(Bucket=self.bucket, Key=key)
#             return resp["Body"].read()
#         except ClientError as e:
#             raise FileNotFoundError(f"S3 object not found: {key}") from e

#     def delete(self, key: str) -> bool:
#         """Delete object from S3; return True if deleted."""
#         try:
#             self.s3.delete_object(Bucket=self.bucket, Key=key)
#             return True
#         except ClientError:
#             return False
