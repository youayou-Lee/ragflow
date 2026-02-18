#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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

from common import (
    document_subdocs_generate,
    document_subdocs_list,
    document_subdocs_save,
    list_documents,
    upload_documents,
)


@pytest.mark.p2
class TestSubDocumentWorkflow:
    def test_generate_and_list_subdocs(self, WebApiAuth, add_dataset_func, generate_test_files):
        kb_id = add_dataset_func
        pdf = generate_test_files["pdf"]

        upload_res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [pdf])
        assert upload_res["code"] == 0, upload_res
        doc_id = upload_res["data"][0]["id"]

        gen_res = document_subdocs_generate(WebApiAuth, {"doc_id": doc_id})
        assert gen_res["code"] == 0, gen_res
        assert gen_res["data"]["doc_id"] == doc_id, gen_res
        assert isinstance(gen_res["data"]["sub_docs"], list), gen_res

        list_res = document_subdocs_list(WebApiAuth, {"doc_id": doc_id})
        assert list_res["code"] == 0, list_res
        assert list_res["data"]["doc_id"] == doc_id, list_res
        assert isinstance(list_res["data"]["sub_docs"], list), list_res

    def test_save_subdocs(self, WebApiAuth, add_dataset_func, generate_test_files):
        kb_id = add_dataset_func
        pdf = generate_test_files["pdf"]
        upload_res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [pdf])
        assert upload_res["code"] == 0, upload_res
        doc_id = upload_res["data"][0]["id"]

        payload = {
            "doc_id": doc_id,
            "sub_docs": [
                {
                    "name": "manual-subdoc-1",
                    "start_page": 1,
                    "end_page": 1,
                    "doc_type": "indictment",
                    "confidence": 1.0,
                    "status": "ready",
                }
            ],
        }
        save_res = document_subdocs_save(WebApiAuth, payload)
        assert save_res["code"] == 0, save_res
        assert save_res["data"]["sub_docs"][0]["name"] == "manual-subdoc-1", save_res

        list_res = document_subdocs_list(WebApiAuth, {"doc_id": doc_id})
        assert list_res["code"] == 0, list_res
        assert list_res["data"]["sub_docs"][0]["name"] == "manual-subdoc-1", list_res


@pytest.mark.p3
class TestSubDocumentNegative:
    def test_generate_requires_pdf(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        txt = tmp_path / "subdoc_non_pdf.txt"
        txt.write_text("hello")
        upload_res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [txt])
        assert upload_res["code"] == 0, upload_res
        doc_id = upload_res["data"][0]["id"]

        gen_res = document_subdocs_generate(WebApiAuth, {"doc_id": doc_id})
        assert gen_res["code"] == 102, gen_res
        assert "only supports PDF" in gen_res["message"], gen_res

    def test_save_subdocs_invalid_range(self, WebApiAuth, add_dataset_func, generate_test_files):
        kb_id = add_dataset_func
        pdf = generate_test_files["pdf"]
        upload_res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [pdf])
        assert upload_res["code"] == 0, upload_res
        doc_id = upload_res["data"][0]["id"]

        bad_payload = {
            "doc_id": doc_id,
            "sub_docs": [{"start_page": 2, "end_page": 1}],
        }
        save_res = document_subdocs_save(WebApiAuth, bad_payload)
        assert save_res["code"] == 101, save_res
        assert "Invalid page range" in save_res["message"], save_res

    def test_list_subdocs_no_auth_doc(self, WebApiAuth):
        res = document_subdocs_list(WebApiAuth, {"doc_id": "not_exist"})
        assert res["code"] in [103, 109], res
