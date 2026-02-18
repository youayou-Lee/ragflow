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
from api.db.db_models import DB, DocumentSubdoc
from api.db.services.common_service import CommonService


class DocumentSubdocService(CommonService):
    model = DocumentSubdoc

    @classmethod
    @DB.connection_context()
    def list_by_doc_id(cls, doc_id: str):
        return list(cls.model.select().where(cls.model.doc_id == doc_id).order_by(cls.model.start_page.asc(), cls.model.create_time.asc()).dicts())

    @classmethod
    @DB.connection_context()
    def list_by_ids(cls, sub_doc_ids: list[str]):
        if not sub_doc_ids:
            return []
        return list(cls.model.select().where(cls.model.id.in_(sub_doc_ids)).dicts())

    @classmethod
    @DB.connection_context()
    def get_max_version_no(cls, doc_id: str) -> int:
        row = cls.model.select(cls.model.version_no).where(cls.model.doc_id == doc_id).order_by(cls.model.version_no.desc()).first()
        return int(row.version_no) if row else 0
