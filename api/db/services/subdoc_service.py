from typing import Iterable

from api.db.db_models import DB, DocumentSubDoc
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid


class SubDocService(CommonService):
    model = DocumentSubDoc

    @classmethod
    @DB.connection_context()
    def create(cls, doc_id: str, name: str, start_page: int, end_page: int, doc_type: str,
               confidence: float = 0.0, status: str = "1", created_by: str = ""):
        return cls.insert(
            id=get_uuid(),
            doc_id=doc_id,
            name=name,
            start_page=start_page,
            end_page=end_page,
            doc_type=doc_type,
            confidence=confidence,
            status=status,
            created_by=created_by,
        )

    @classmethod
    @DB.connection_context()
    def list(cls, doc_id: str = None, status: str = None, doc_type: str = None):
        query = cls.model.select()
        if doc_id is not None:
            query = query.where(cls.model.doc_id == doc_id)
        if status is not None:
            query = query.where(cls.model.status == status)
        if doc_type is not None:
            query = query.where(cls.model.doc_type == doc_type)
        return query.order_by(cls.model.start_page.asc(), cls.model.create_time.asc())

    @classmethod
    @DB.connection_context()
    def update_status(cls, sub_doc_id: str, status: str):
        return cls.update_by_id(sub_doc_id, {"status": status})

    @classmethod
    @DB.connection_context()
    def bulk_replace(cls, doc_id: str, sub_docs: Iterable[dict], created_by: str = ""):
        cls.model.delete().where(cls.model.doc_id == doc_id).execute()
        payload = []
        for item in sub_docs:
            payload.append(
                {
                    "id": item.get("id") or get_uuid(),
                    "doc_id": doc_id,
                    "name": item["name"],
                    "start_page": item.get("start_page", 1),
                    "end_page": item.get("end_page", 1),
                    "doc_type": item.get("doc_type", ""),
                    "confidence": item.get("confidence", 0.0),
                    "status": item.get("status", "1"),
                    "created_by": item.get("created_by") or created_by,
                }
            )
        if payload:
            cls.insert_many(payload)
        return payload

    @classmethod
    @DB.connection_context()
    def delete_by_doc_id(cls, doc_id: str):
        return cls.model.delete().where(cls.model.doc_id == doc_id).execute()
