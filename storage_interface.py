#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Storage Interface for FusionSolar Power Adjustment

This module provides an interface and implementations for different storage solutions.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional
from config import STORAGE_TYPE, S3_BUCKET_NAME, S3_REGION, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, \
    LOCAL_STORAGE_DIR

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StorageInterface(ABC):
    """
    Abstract interface for file storage operations.
    
    This interface defines the contract for different storage implementations,
    such as local filesystem, AWS S3, or other storage services.
    """
    
    @abstractmethod
    def write_binary(self, path: str, content: bytes) -> bool:
        """
        Write binary content to a file at the specified path.
        
        Args:
            path (str): The path where the file should be stored
            content (bytes): The binary content to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def read_binary(self, path: str) -> Optional[bytes]:
        """
        Read binary content from a file at the specified path.
        
        Args:
            path (str): The path of the file to read
            
        Returns:
            Optional[bytes]: The binary content if successful, None otherwise
        """
        pass
    
    def write_text(self, path: str, content: str) -> bool:
        """
        Write text content to a file at the specified path.
        
        This is a convenience method that delegates to write_binary.
        
        Args:
            path (str): The path where the file should be stored
            content (str): The text content to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.write_binary(path, content.encode('utf-8'))
    
    def read_text(self, path: str) -> Optional[str]:
        """
        Read text content from a file at the specified path.
        
        This is a convenience method that delegates to read_binary.
        
        Args:
            path (str): The path of the file to read
            
        Returns:
            Optional[str]: The text content if successful, None otherwise
        """
        binary_content = self.read_binary(path)
        if binary_content is None:
            return None
        return binary_content.decode('utf-8')
    
    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists at the specified path.
        
        Args:
            path (str): The path to check
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        pass

class LocalFileStorage(StorageInterface):
    """
    Implementation of the StorageInterface using the local filesystem.
    """
    def __init__(self, storage_dir: str):
        self.ensure_directory_exists(storage_dir)
        self.storage_dir = storage_dir

    def write_binary(self, path: str, content: bytes) -> bool:
        """
        Write binary content to a file on the local filesystem.
        
        Args:
            path (str): The path where the file should be stored relative to the storage_dir
            content (bytes): The binary content to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        path = self.fq_path(path)

        # ensure the directory exists
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

        try:
            # Write the content to the file
            with open(path, 'wb') as file:
                file.write(content)
            logger.debug(f"Successfully wrote {len(content)} bytes to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing to file {path}: {e}")
            return False
    
    def read_binary(self, path: str) -> Optional[bytes]:
        """
        Read binary content from a file on the local filesystem.
        
        Args:
            path (str): The path of the file to read
            
        Returns:
            Optional[bytes]: The binary content if successful, None otherwise
        """
        path = self.fq_path(path)
        try:
            if not self.file_exists(path):
                logger.debug(f"File does not exist: {path}")
                return None
                
            with open(path, 'rb') as file:
                content = file.read()
            logger.debug(f"Successfully read {len(content)} bytes from {path}")
            return content
            
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return None
    
    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists on the local filesystem.
        
        Args:
            path (str): The path to check
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        return os.path.isfile(path)
    
    @staticmethod
    def ensure_directory_exists(path: str) -> bool:
        """
        Ensure that a directory exists on the local filesystem.
        
        Args:
            path (str): The directory path to ensure exists
            
        Returns:
            bool: True if the directory exists or was created, False otherwise
        """
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                logger.debug(f"Created directory: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False

    def fq_path(self, path: str) -> str:
        return os.path.join(self.storage_dir, path)


class S3Storage(StorageInterface):
    """
    Implementation of the StorageInterface using AWS S3.
    """
    
    def __init__(self, bucket_name: str, aws_region: str = None, 
                 aws_access_key_id: str = None, aws_secret_access_key: str = None):
        """
        Initialize the S3 storage interface.
        
        Args:
            bucket_name (str): The name of the S3 bucket to use
            aws_region (str, optional): AWS region. Defaults to None (uses boto3 default).
            aws_access_key_id (str, optional): AWS access key ID. Defaults to None (uses boto3 default).
            aws_secret_access_key (str, optional): AWS secret access key. Defaults to None (uses boto3 default).
        """
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            
            self.bucket_name = bucket_name
            
            # Create an S3 client
            self.s3_client = boto3.client(
                's3',
                region_name=aws_region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            
            # Test the connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {bucket_name}")
            
        except ImportError:
            logger.error("Failed to import boto3. Please install it with 'pip install boto3'")
            raise ImportError("boto3 is required for S3Storage. Install with 'pip install boto3'")
        except (NoCredentialsError, ClientError) as e:
            logger.error(f"Failed to connect to S3 bucket {bucket_name}: {e}")
            raise Exception(f"Failed to connect to S3 bucket: {e}")
    
    def write_binary(self, path: str, content: bytes) -> bool:
        """
        Write binary content to a file in S3.
        
        Args:
            path (str): The path (key) where the file should be stored in S3
            content (bytes): The binary content to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from botocore.exceptions import ClientError
            
            # Upload the content directly to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=content
            )
            logger.debug(f"Successfully wrote {len(content)} bytes to s3://{self.bucket_name}/{path}")
            return True
            
        except ClientError as e:
            logger.error(f"Error writing to S3 file s3://{self.bucket_name}/{path}: {e}")
            return False
    
    def read_binary(self, path: str) -> Optional[bytes]:
        """
        Read binary content from a file in S3.
        
        Args:
            path (str): The path (key) of the file to read in S3
            
        Returns:
            Optional[bytes]: The binary content if successful, None otherwise
        """
        try:
            from botocore.exceptions import ClientError
            
            if not self.file_exists(path):
                logger.debug(f"File does not exist: s3://{self.bucket_name}/{path}")
                return None
                
            # Get the object from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=path
            )
            
            # Read the content
            content = response['Body'].read()
            logger.debug(f"Successfully read {len(content)} bytes from s3://{self.bucket_name}/{path}")
            return content
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"File does not exist: s3://{self.bucket_name}/{path}")
                return None
            logger.error(f"Error reading S3 file s3://{self.bucket_name}/{path}: {e}")
            return None
    
    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            path (str): The path (key) to check in S3
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            from botocore.exceptions import ClientError
            
            # Try to get the object head
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=path
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking if S3 file exists s3://{self.bucket_name}/{path}: {e}")
            return False


def create_storage() -> StorageInterface:
    """
    Factory function to create the appropriate storage implementation based on configuration.

    Returns:
        StorageInterface: The configured storage implementation
    """
    if STORAGE_TYPE.lower() == "s3":
        logger.info(f"Using S3 storage with bucket: {S3_BUCKET_NAME}")
        return S3Storage(
            bucket_name=S3_BUCKET_NAME,
            aws_region=S3_REGION,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY
        )
    else:
        logger.info(f"Using local file storage at: {LOCAL_STORAGE_DIR}")
        return LocalFileStorage(LOCAL_STORAGE_DIR)
