from app.database import SessionLocal
from app.models import SentimentAuditRecord
from app.sentiment.audit import SentimentAuditLogger

db = SessionLocal()

try:
    record = (
        db.query(SentimentAuditRecord)
        .filter(SentimentAuditRecord.id == 4)
        .first()
    )

    print("ID:", record.id)
    print("tenant_id:", repr(record.tenant_id), type(record.tenant_id))
    print("event_type:", repr(record.event_type), type(record.event_type))
    print("customer_id:", repr(record.customer_id), type(record.customer_id))
    print("job_id:", repr(record.job_id), type(record.job_id))
    print("manager_id:", repr(record.manager_id), type(record.manager_id))
    print("input_text:", repr(record.input_text), type(record.input_text))
    print("sentiment_label:", repr(record.sentiment_label), type(record.sentiment_label))
    print("confidence:", repr(record.confidence), type(record.confidence))
    print("model_used:", repr(record.model_used), type(record.model_used))
    print("cost:", repr(record.cost), type(record.cost))
    print("trigger_reason:", repr(record.trigger_reason), type(record.trigger_reason))
    print("action:", repr(record.action), type(record.action))
    print("notes:", repr(record.notes), type(record.notes))
    print("timestamp:", repr(record.timestamp), type(record.timestamp))
    print("timestamp iso:", record.timestamp.isoformat())
    print("sequence_number:", repr(record.sequence_number), type(record.sequence_number))
    print("previous_hash:", repr(record.previous_hash))
    print("stored hash:", record.record_hash)

    calculated = SentimentAuditLogger._calculate_record_hash(
        tenant_id=record.tenant_id,
        event_type=record.event_type,
        customer_id=record.customer_id,
        job_id=record.job_id,
        manager_id=record.manager_id,
        input_text=record.input_text,
        sentiment_label=record.sentiment_label,
        confidence=record.confidence,
        model_used=record.model_used,
        cost=record.cost,
        trigger_reason=record.trigger_reason,
        action=record.action,
        notes=record.notes,
        timestamp=record.timestamp,
        sequence_number=record.sequence_number,
        previous_hash=record.previous_hash,
    )

    print("calculated hash:", calculated)

finally:
    db.close()
