from sqlalchemy import asc, desc
from ..extensions import db
from ..models import Application, DataModel, DataRecord, checksum_for


def get_model(app: Application, slug: str) -> DataModel | None:
    return DataModel.query.filter_by(application_id=app.id, slug=slug, enabled=True).first()


def validate_payload(model: DataModel, payload: dict) -> list[str]:
    schema = model.schema_json or {}
    fields = schema.get('fields') or {}
    if not isinstance(fields, dict):
        return []
    errors = []
    for name, spec in fields.items():
        spec = spec if isinstance(spec, dict) else {}
        required = spec.get('required') is True
        if required and (name not in payload or payload[name] in (None, '')):
            errors.append(f'{name}:required')
            continue
        if name not in payload or payload[name] is None:
            continue
        kind = spec.get('type')
        value = payload[name]
        ok = {
            'string': isinstance(value, str),
            'number': isinstance(value, (int, float)) and not isinstance(value, bool),
            'integer': isinstance(value, int) and not isinstance(value, bool),
            'boolean': isinstance(value, bool),
            'object': isinstance(value, dict),
            'array': isinstance(value, list),
        }.get(kind, True)
        if not ok:
            errors.append(f'{name}:invalid_type')
    return errors


def serialize_record(record: DataRecord) -> dict:
    return {
        'id': record.record_key,
        'key': record.record_key,
        'version': record.version,
        'checksum': record.checksum,
        'deleted': record.deleted,
        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
        'data': record.payload_json or {},
    }


def list_records(model: DataModel, page: int, per_page: int, include_deleted: bool = False):
    query = DataRecord.query.filter_by(model_id=model.id)
    if not include_deleted:
        query = query.filter_by(deleted=False)
    query = query.order_by(desc(DataRecord.updated_at), desc(DataRecord.id))
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return [serialize_record(r) for r in items], total


def create_record(model: DataModel, record_key: str, payload: dict):
    errors = validate_payload(model, payload)
    if errors:
        return None, errors, None
    existing = DataRecord.query.filter_by(model_id=model.id, record_key=record_key).first()
    if existing and not existing.deleted:
        return existing, [], 'exists'
    if existing:
        existing.deleted = False
        existing.version += 1
        existing.payload_json = payload
        existing.recalc()
        db.session.add(existing)
        db.session.commit()
        return existing, [], 'restored'
    record = DataRecord(model_id=model.id, record_key=record_key, version=1, payload_json=payload)
    record.recalc()
    db.session.add(record)
    db.session.commit()
    return record, [], 'created'


def update_record(model: DataModel, record: DataRecord, payload: dict, base_version: int | None):
    errors = validate_payload(model, payload)
    if errors:
        return None, errors, 'validation'
    if base_version is not None and base_version != record.version:
        return record, [], 'conflict'
    record.payload_json = payload
    record.version += 1
    record.deleted = False
    record.recalc()
    db.session.add(record)
    db.session.commit()
    return record, [], 'updated'


def delete_record(record: DataRecord, base_version: int | None):
    if base_version is not None and base_version != record.version:
        return record, 'conflict'
    record.deleted = True
    record.version += 1
    db.session.add(record)
    db.session.commit()
    return record, 'deleted'
