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
"""Setup runner for criminal benchmark - login, dataset, documents."""

import time
from pathlib import Path
from typing import Optional

import requests


class BenchmarkSetup:
    """Handles setup operations for benchmark testing."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token: Optional[str] = None
        self.session = requests.Session()

    def login(self) -> bool:
        """Login and get API token."""
        url = f"{self.base_url}/v1/user/login"
        payload = {
            "email": self.email,
            "password": self.password,
        }

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Login failed: {data.get('message')}")

        self.token = data["data"].get("authorization_token")
        if not self.token:
            # Try to get from cookies
            for cookie in self.session.cookies:
                if cookie.name == "authorization_token":
                    self.token = cookie.value
                    break

        if not self.token:
            raise RuntimeError("No token received after login")

        # Set authorization header
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        return True

    def create_dataset(self, name: str, embedding_model: str, chunk_method: str = "naive") -> str:
        """Create a new dataset and return its ID."""
        url = f"{self.base_url}/api/v1/datasets"
        payload = {
            "name": name,
            "embedding_model": embedding_model,
            "chunk_method": chunk_method,
        }

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create dataset failed: {data.get('message')}")

        return data["data"]["id"]

    def upload_document(self, dataset_id: str, file_path: str) -> str:
        """Upload a document to dataset and return document ID."""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        with path.open("rb") as f:
            files = {"file": (path.name, f)}
            resp = self.session.post(url, files=files)

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Upload document failed: {data.get('message')}")

        # Return first document ID
        return data["data"][0]["id"]

    def parse_document(self, dataset_id: str, document_ids: list[str]) -> bool:
        """Trigger document parsing."""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks"
        payload = {"document_ids": document_ids}

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Parse document failed: {data.get('message')}")

        return True

    def wait_for_parsing(
        self,
        dataset_id: str,
        document_ids: list[str],
        timeout: float = 300,
        interval: float = 5,
    ) -> bool:
        """Wait for all documents to finish parsing."""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        start_time = time.time()

        while time.time() - start_time < timeout:
            resp = self.session.get(url)
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(f"List documents failed: {data.get('message')}")

            docs = {d["id"]: d for d in data["data"].get("docs", [])}

            all_done = True
            for doc_id in document_ids:
                doc = docs.get(doc_id)
                if not doc or doc.get("run") != "DONE":
                    all_done = False
                    break

            if all_done:
                return True

            time.sleep(interval)

        raise TimeoutError(f"Document parsing timeout after {timeout}s")

    def create_chat_assistant(self, name: str, dataset_ids: list[str], llm_model: str) -> str:
        """Create a chat assistant and return its ID."""
        url = f"{self.base_url}/api/v1/chats"
        payload = {
            "name": name,
            "dataset_ids": dataset_ids,
            "llm": {"model_name": llm_model},
        }

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create chat assistant failed: {data.get('message')}")

        return data["data"]["id"]

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset."""
        url = f"{self.base_url}/api/v1/datasets"
        payload = {"ids": [dataset_id]}

        resp = self.session.delete(url, json=payload)
        data = resp.json()

        return data.get("code") == 0

    def delete_chat_assistant(self, chat_id: str) -> bool:
        """Delete a chat assistant."""
        url = f"{self.base_url}/api/v1/chats"
        payload = {"ids": [chat_id]}

        resp = self.session.delete(url, json=payload)
        data = resp.json()

        return data.get("code") == 0
