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
"""Integration test fixtures for RAGFlow legal document processing.

This module provides pytest fixtures for integration testing:
- Authentication and API setup
- Test sample file management
- Prebuilt dataset access (for parse/format tests)
- Temporary dataset lifecycle (for upload/e2e tests)
"""

import time
from pathlib import Path
from typing import Generator, Optional

import pytest
import yaml

# Add parent paths for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from test.eval.evaluator.setup import EvaluationSetup


def load_config() -> dict:
    """Load test configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def integration_setup() -> Generator[EvaluationSetup, None, None]:
    """Create and login an EvaluationSetup instance for integration tests.

    This fixture:
    1. Loads configuration from config.yaml
    2. Creates EvaluationSetup instance
    3. Performs login
    4. Yields the setup for test use
    """
    config = load_config()

    setup = EvaluationSetup(
        base_url=config["server"]["base_url"],
        email=config["auth"]["email"],
        password=config["auth"]["password"],
    )

    setup.login()
    yield setup


@pytest.fixture(scope="module")
def sample_files() -> dict[str, Path]:
    """Provide paths to test sample files.

    Returns:
        Dictionary mapping sample type to file path:
        - "indictment": Sample indictment document
        - "interrogation": Sample interrogation record
    """
    fixtures_dir = Path(__file__).parent / "fixtures"

    # Check if fixtures exist, otherwise use benchmark samples
    samples = {
        "indictment": fixtures_dir / "sample_indictment.pdf",
        "interrogation": fixtures_dir / "sample_interrogation.pdf",
    }

    # Fall back to benchmark samples if fixtures don't exist
    benchmark_dir = Path(__file__).parent.parent.parent.parent / "benchmark"
    fallbacks = {
        "indictment": benchmark_dir / "起诉意见书/曾庆成危险驾驶案/原始数据/起诉意见书_sample.pdf",
        "interrogation": benchmark_dir / "讯问笔录/陈明飞诈骗案/原始数据/讯问笔录_sample.pdf",
    }

    for key, path in samples.items():
        if not path.exists():
            samples[key] = fallbacks.get(key, path)

    return samples


@pytest.fixture
def test_config() -> dict:
    """Provide test configuration dictionary."""
    return load_config()


# =============================================================================
# Prebuilt Dataset Fixtures (for parse and format validation tests)
# =============================================================================


@pytest.fixture(scope="module")
def prebuilt_dataset_ids() -> dict[str, Optional[str]]:
    """Provide prebuilt dataset IDs from config.

    These datasets should be created manually and contain pre-parsed documents.
    Used for parse and format validation tests to avoid repeated setup.

    Returns:
        Dictionary with dataset IDs:
        - indictment_single: Single indictment document dataset
        - indictment_multiple: Multiple indictment documents dataset
        - interrogation_single: Single interrogation document dataset
        - interrogation_multiple: Multiple interrogation documents dataset
    """
    config = load_config()
    prebuilt = config.get("prebuilt_datasets", {})
    return {
        "indictment_single": prebuilt.get("indictment_single") or None,
        "indictment_multiple": prebuilt.get("indictment_multiple") or None,
        "interrogation_single": prebuilt.get("interrogation_single") or None,
        "interrogation_multiple": prebuilt.get("interrogation_multiple") or None,
    }


@pytest.fixture
def indictment_single_dataset(
    integration_setup: EvaluationSetup,
    prebuilt_dataset_ids: dict[str, Optional[str]],
) -> str:
    """Get the prebuilt single indictment dataset ID.

    Raises pytest.skip if not configured.
    """
    dataset_id = prebuilt_dataset_ids.get("indictment_single")
    if not dataset_id:
        pytest.skip(
            "Prebuilt indictment_single dataset not configured. "
            "Please create it and add ID to config.yaml"
        )
    return dataset_id


@pytest.fixture
def indictment_multiple_dataset(
    integration_setup: EvaluationSetup,
    prebuilt_dataset_ids: dict[str, Optional[str]],
) -> str:
    """Get the prebuilt multiple indictment dataset ID.

    Raises pytest.skip if not configured.
    """
    dataset_id = prebuilt_dataset_ids.get("indictment_multiple")
    if not dataset_id:
        pytest.skip(
            "Prebuilt indictment_multiple dataset not configured. "
            "Please create it and add ID to config.yaml"
        )
    return dataset_id


@pytest.fixture
def interrogation_single_dataset(
    integration_setup: EvaluationSetup,
    prebuilt_dataset_ids: dict[str, Optional[str]],
) -> str:
    """Get the prebuilt single interrogation dataset ID.

    Raises pytest.skip if not configured.
    """
    dataset_id = prebuilt_dataset_ids.get("interrogation_single")
    if not dataset_id:
        pytest.skip(
            "Prebuilt interrogation_single dataset not configured. "
            "Please create it and add ID to config.yaml"
        )
    return dataset_id


@pytest.fixture
def interrogation_multiple_dataset(
    integration_setup: EvaluationSetup,
    prebuilt_dataset_ids: dict[str, Optional[str]],
) -> str:
    """Get the prebuilt multiple interrogation dataset ID.

    Raises pytest.skip if not configured.
    """
    dataset_id = prebuilt_dataset_ids.get("interrogation_multiple")
    if not dataset_id:
        pytest.skip(
            "Prebuilt interrogation_multiple dataset not configured. "
            "Please create it and add ID to config.yaml"
        )
    return dataset_id


# =============================================================================
# Temporary Dataset Fixtures (for upload and e2e tests - auto cleanup)
# =============================================================================


@pytest.fixture
def temp_dataset_for_upload(
    integration_setup: EvaluationSetup,
) -> Generator[str, None, None]:
    """Create a temporary dataset for upload tests, automatically cleaned up after test.

    This fixture creates a fresh dataset for each upload test and ensures cleanup.
    """
    config = load_config()
    dataset_name = f"upload_test_{int(time.time() * 1000)}"

    dataset_id = integration_setup.create_dataset(
        name=dataset_name,
        embedding_model=config["dataset"]["embedding_model"],
        chunk_method=config["dataset"]["chunk_method"],
    )

    try:
        yield dataset_id
    finally:
        try:
            integration_setup.delete_dataset(dataset_id)
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
def temp_dataset_for_e2e(
    integration_setup: EvaluationSetup,
) -> Generator[str, None, None]:
    """Create a temporary dataset for end-to-end tests, automatically cleaned up after test.

    This fixture creates a fresh dataset for each e2e test and ensures cleanup.
    """
    config = load_config()
    dataset_name = f"e2e_test_{int(time.time() * 1000)}"

    dataset_id = integration_setup.create_dataset(
        name=dataset_name,
        embedding_model=config["dataset"]["embedding_model"],
        chunk_method=config["dataset"]["chunk_method"],
    )

    try:
        yield dataset_id
    finally:
        try:
            integration_setup.delete_dataset(dataset_id)
        except Exception:
            pass  # Ignore cleanup errors


# =============================================================================
# Legacy fixture for backward compatibility
# =============================================================================


@pytest.fixture
def temp_dataset(
    integration_setup: EvaluationSetup,
) -> Generator[str, None, None]:
    """Create a temporary dataset for testing, automatically cleaned up after test.

    Note: This is kept for backward compatibility. Prefer using
    temp_dataset_for_upload or temp_dataset_for_e2e for clarity.
    """
    config = load_config()
    dataset_name = f"integration_test_{int(time.time() * 1000)}"

    dataset_id = integration_setup.create_dataset(
        name=dataset_name,
        embedding_model=config["dataset"]["embedding_model"],
        chunk_method=config["dataset"]["chunk_method"],
    )

    try:
        yield dataset_id
    finally:
        try:
            integration_setup.delete_dataset(dataset_id)
        except Exception:
            pass  # Ignore cleanup errors
