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
import pytest
from rag.llm.chat_model import LLMErrorCode, is_recoverable_error, RECOVERABLE_ERRORS


pytestmark = pytest.mark.p1


class TestRecoverableErrors:
    def test_rate_limit_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_RATE_LIMIT) is True

    def test_server_error_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_SERVER) is True

    def test_timeout_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_TIMEOUT) is True

    def test_connection_error_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_CONNECTION) is True

    def test_quota_exceeded_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_QUOTA) is True

    def test_auth_error_is_not_recoverable(self):
        """Authentication errors should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_AUTHENTICATION) is False

    def test_content_filter_is_not_recoverable(self):
        """Content filter errors should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_CONTENT_FILTER) is False

    def test_model_error_is_not_recoverable(self):
        """Model errors (like model not found) should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_MODEL) is False

    def test_invalid_request_is_not_recoverable(self):
        """Invalid request errors should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_INVALID_REQUEST) is False

    def test_generic_error_is_not_recoverable(self):
        """Generic errors should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_GENERIC) is False

    def test_recoverable_errors_set_is_correct(self):
        """RECOVERABLE_ERRORS set should contain expected errors"""
        assert LLMErrorCode.ERROR_RATE_LIMIT in RECOVERABLE_ERRORS
        assert LLMErrorCode.ERROR_SERVER in RECOVERABLE_ERRORS
        assert LLMErrorCode.ERROR_TIMEOUT in RECOVERABLE_ERRORS
        assert LLMErrorCode.ERROR_CONNECTION in RECOVERABLE_ERRORS
        assert LLMErrorCode.ERROR_QUOTA in RECOVERABLE_ERRORS
