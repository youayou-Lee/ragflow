from api.db.db_models import DB, SubDocVersion
from api.db.services.common_service import CommonService
from api.db.services.subdoc_service import SubDocService
from common.misc_utils import get_uuid


class SubDocVersionService(CommonService):
    model = SubDocVersion

    @classmethod
    @DB.connection_context()
    def append_version(cls, sub_doc_id: str, change_summary: str, payload_json: dict, version_no: int = None):
        if version_no is None:
            latest = (
                cls.model.select(cls.model.version_no)
                .where(cls.model.sub_doc_id == sub_doc_id)
                .order_by(cls.model.version_no.desc())
                .first()
            )
            version_no = (latest.version_no if latest else 0) + 1

        return cls.insert(
            id=get_uuid(),
            sub_doc_id=sub_doc_id,
            version_no=version_no,
            change_summary=change_summary,
            payload_json=payload_json or {},
        )

    @classmethod
    @DB.connection_context()
    def list_versions(cls, sub_doc_id: str):
        return (
            cls.model.select()
            .where(cls.model.sub_doc_id == sub_doc_id)
            .order_by(cls.model.version_no.desc(), cls.model.create_time.desc())
        )

    @classmethod
    @DB.connection_context()
    def rollback(cls, sub_doc_id: str, version_no: int):
        target = cls.model.get_or_none(
            cls.model.sub_doc_id == sub_doc_id,
            cls.model.version_no == version_no,
        )
        if not target:
            return False, None

        payload = target.payload_json or {}
        update_data = {
            "name": payload.get("name"),
            "start_page": payload.get("start_page"),
            "end_page": payload.get("end_page"),
            "doc_type": payload.get("doc_type"),
            "confidence": payload.get("confidence"),
            "status": payload.get("status"),
        }
        update_data = {k: v for k, v in update_data.items() if v is not None}
        if update_data:
            SubDocService.update_by_id(sub_doc_id, update_data)
        return True, target

    @classmethod
    @DB.connection_context()
    def delete_by_sub_doc_ids(cls, sub_doc_ids):
        if not sub_doc_ids:
            return 0
        return cls.model.delete().where(cls.model.sub_doc_id.in_(sub_doc_ids)).execute()
