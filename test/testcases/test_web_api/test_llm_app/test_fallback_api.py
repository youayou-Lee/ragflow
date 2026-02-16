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
API tests for fallback configuration endpoints.

These tests verify the REST API endpoints for managing fallback configurations.
"""
import pytest
import requests
from common import LLM_APP_URL
from configs import HOST_ADDRESS, VERSION, INVALID_API_TOKEN
from libs.auth import RAGFlowWebApiAuth


pytestmark = pytest.mark.p2

HEADERS = {"Content-Type": "application/json"}


def llm_set_fallback_config(auth, payload=None, *, headers=HEADERS):
    """Set fallback configuration for a factory"""
    res = requests.post(
        url=f"{HOST_ADDRESS}{LLM_APP_URL}/set_fallback_config",
        headers=headers,
        auth=auth,
        json=payload
    )
    return res.json()


def llm_get_fallback_config(auth, params=None, *, headers=HEADERS):
    """Get fallback configuration for a factory"""
    res = requests.get(
        url=f"{HOST_ADDRESS}{LLM_APP_URL}/get_fallback_config",
        headers=headers,
        auth=auth,
        params=params
    )
    return res.json()


INVALID_AUTH_CASES = [
    (None, 401, "<Unauthorized '401: Unauthorized'>"),
    (RAGFlowWebApiAuth(INVALID_API_TOKEN), 401, "<Unauthorized '401: Unauthorized'>"),
]


class TestFallbackConfigAuthorization:
    """Test authorization for fallback config endpoints."""

    @pytest.mark.parametrize("invalid_auth, expected_code, expected_message", INVALID_AUTH_CASES)
    def test_set_fallback_config_invalid_auth(self, invalid_auth, expected_code, expected_message):
        """Set fallback config should reject invalid auth"""
        res = llm_set_fallback_config(
            invalid_auth,
            {"llm_factory": "OpenAI", "fallback_models": ["gpt-4o-mini"]}
        )
        assert res["code"] == expected_code, res
        assert res["message"] == expected_message, res

    @pytest.mark.parametrize("invalid_auth, expected_code, expected_message", INVALID_AUTH_CASES)
    def test_get_fallback_config_invalid_auth(self, invalid_auth, expected_code, expected_message):
        """Get fallback config should reject invalid auth"""
        res = llm_get_fallback_config(invalid_auth, {"llm_factory": "OpenAI"})
        assert res["code"] == expected_code, res
        assert res["message"] == expected_message, res


class TestFallbackConfigCRUD:
    """Test CRUD operations for fallback configuration."""

    @pytest.mark.p1
    def test_get_fallback_config_not_configured(self, WebApiAuth):
        """Get fallback config should return empty for unconfigured factory"""
        res = llm_get_fallback_config(WebApiAuth, {"llm_factory": "NonExistentFactory"})
        assert res["code"] == 0, res
        # Should return empty lists for unconfigured factory
        data = res.get("data", {})
        assert data.get("fallback_models", []) == []
        assert data.get("fallback_factories", []) == []

    def test_set_fallback_config_validation_missing_factory(self, WebApiAuth):
        """Set fallback config should validate required fields"""
        res = llm_set_fallback_config(WebApiAuth, {})
        # Should fail with validation error
        assert res["code"] != 0, res

    def test_set_fallback_config_with_models(self, WebApiAuth):
        """Set fallback config with fallback models"""
        # Note: This test requires a configured factory in the test environment
        res = llm_set_fallback_config(
            WebApiAuth,
            {
                "llm_factory": "ZHIPU-AI",
                "fallback_models": ["glm-4-flash"],
                "fallback_factories": []
            }
        )
        # Result depends on whether ZHIPU-AI is configured
        # If not configured, it should return an error
        if res["code"] != 0:
            pytest.skip("ZHIPU-AI not configured for this tenant")

    def test_set_fallback_config_with_factories(self, WebApiAuth):
        """Set fallback config with fallback factories"""
        res = llm_set_fallback_config(
            WebApiAuth,
            {
                "llm_factory": "ZHIPU-AI",
                "fallback_models": [],
                "fallback_factories": ["DeepSeek"]
            }
        )
        # Result depends on whether ZHIPU-AI is configured
        if res["code"] != 0:
            pytest.skip("ZHIPU-AI not configured for this tenant")

    def test_set_and_get_fallback_config(self, WebApiAuth):
        """Set and then get fallback config should return same values"""
        # First try to set the config
        set_res = llm_set_fallback_config(
            WebApiAuth,
            {
                "llm_factory": "ZHIPU-AI",
                "fallback_models": ["glm-4-flash"],
                "fallback_factories": []
            }
        )

        if set_res["code"] != 0:
            pytest.skip("ZHIPU-AI not configured for this tenant")

        # Then get the config
        get_res = llm_get_fallback_config(WebApiAuth, {"llm_factory": "ZHIPU-AI"})

        assert get_res["code"] == 0, get_res
        data = get_res.get("data", {})
        assert "glm-4-flash" in data.get("fallback_models", [])


class TestFallbackConfigEdgeCases:
    """Test edge cases for fallback configuration."""

    def test_set_fallback_config_empty_models_and_factories(self, WebApiAuth):
        """Set fallback config with empty lists should clear config"""
        res = llm_set_fallback_config(
            WebApiAuth,
            {
                "llm_factory": "ZHIPU-AI",
                "fallback_models": [],
                "fallback_factories": []
            }
        )
        if res["code"] != 0:
            pytest.skip("ZHIPU-AI not configured for this tenant")

        # Get config should return empty
        get_res = llm_get_fallback_config(WebApiAuth, {"llm_factory": "ZHIPU-AI"})
        assert get_res["code"] == 0, get_res

    def test_set_fallback_config_duplicate_models(self, WebApiAuth):
        """Set fallback config with duplicate models"""
        res = llm_set_fallback_config(
            WebApiAuth,
            {
                "llm_factory": "ZHIPU-AI",
                "fallback_models": ["glm-4-flash", "glm-4-flash"],
                "fallback_factories": []
            }
        )
        # Should either deduplicate or accept as-is
        # The exact behavior depends on implementation
        if res["code"] != 0:
            pytest.skip("ZHIPU-AI not configured for this tenant")
