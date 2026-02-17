#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
OCR Cache Service for caching OCR results to avoid redundant API calls.

This module provides functionality to cache OCR results in MinIO storage,
enabling faster re-parsing of documents without re-invoking the OCR API.
"""

import json
import logging
from typing import Optional

from common import settings


class OCRCacheService:
    """Service for caching and retrieving OCR results."""

    # Cache directory prefix in MinIO
    CACHE_PREFIX = "ocr_cache"

    @staticmethod
    def get_cache_key(doc_id: str) -> str:
        """
        Generate the cache key for a document.

        Args:
            doc_id: The document ID.

        Returns:
            The cache key string.
        """
        return f"{OCRCacheService.CACHE_PREFIX}/{doc_id}.json"

    @staticmethod
    def save_ocr_result(doc_id: str, kb_id: str, ocr_result: dict) -> str:
        """
        Save OCR result to MinIO cache.

        Args:
            doc_id: The document ID.
            kb_id: The knowledge base ID for storage bucket.
            ocr_result: The OCR result dictionary to cache.

        Returns:
            The cache key for the stored result.
        """
        cache_key = OCRCacheService.get_cache_key(doc_id)
        try:
            cache_data = json.dumps(ocr_result, ensure_ascii=False).encode("utf-8")
            settings.STORAGE_IMPL.put(kb_id, cache_key, cache_data)
            logging.info(f"OCR cache saved for doc {doc_id}, key: {cache_key}")
            return cache_key
        except Exception as e:
            logging.exception(f"Failed to save OCR cache for doc {doc_id}: {e}")
            return ""

    @staticmethod
    def load_ocr_result(kb_id: str, cache_key: str) -> Optional[dict]:
        """
        Load OCR result from MinIO cache.

        Args:
            kb_id: The knowledge base ID for storage bucket.
            cache_key: The cache key for the OCR result.

        Returns:
            The cached OCR result dictionary, or None if not found.
        """
        try:
            cache_data = settings.STORAGE_IMPL.get(kb_id, cache_key)
            if cache_data:
                result = json.loads(cache_data.decode("utf-8"))
                logging.info(f"OCR cache loaded from key: {cache_key}")
                return result
            return None
        except Exception as e:
            logging.warning(f"Failed to load OCR cache from {cache_key}: {e}")
            return None

    @staticmethod
    def delete_ocr_cache(doc_id: str, kb_id: str) -> bool:
        """
        Delete OCR cache for a document.

        Args:
            doc_id: The document ID.
            kb_id: The knowledge base ID for storage bucket.

        Returns:
            True if deletion was successful, False otherwise.
        """
        cache_key = OCRCacheService.get_cache_key(doc_id)
        try:
            settings.STORAGE_IMPL.delete(kb_id, cache_key)
            logging.info(f"OCR cache deleted for doc {doc_id}")
            return True
        except Exception as e:
            logging.warning(f"Failed to delete OCR cache for doc {doc_id}: {e}")
            return False

    @staticmethod
    def cache_exists(kb_id: str, cache_key: str) -> bool:
        """
        Check if OCR cache exists for a document.

        Args:
            kb_id: The knowledge base ID for storage bucket.
            cache_key: The cache key to check.

        Returns:
            True if cache exists, False otherwise.
        """
        try:
            # Try to get the object - if it exists, return True
            settings.STORAGE_IMPL.get(kb_id, cache_key)
            return True
        except Exception:
            return False
