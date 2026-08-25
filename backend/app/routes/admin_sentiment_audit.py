from csv import writer
from datetime import datetime
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.database import get_db
from app.sentiment.audit import SentimentAuditLogger


router = APIRouter(
    prefix="/admin/sentiment",
    tags=["Sentiment Audit"],
)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use ISO-8601 format.",
        ) from exc


def _get_records(
    db: Session,
    tenant_id: str,
    customer_id: str | None = None,
    job_id: int | None = None,
    manager_id: str | None = None,
    sentiment_label: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    audit_logger = SentimentAuditLogger(db)

    return audit_logger.search(
        tenant_id=tenant_id,
        customer_id=customer_id,
        job_id=job_id,
        manager_id=manager_id,
        sentiment_label=sentiment_label,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )


@router.get("/audit")
def get_sentiment_audit_logs(
    tenant_id: str,
    customer_id: str | None = None,
    job_id: int | None = None,
    manager_id: str | None = None,
    sentiment_label: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Search sentiment audit records.
    """

    records = _get_records(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        job_id=job_id,
        manager_id=manager_id,
        sentiment_label=sentiment_label,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        {
            "id": record.id,
            "tenant_id": record.tenant_id,
            "event_type": record.event_type,
            "customer_id": record.customer_id,
            "job_id": record.job_id,
            "manager_id": record.manager_id,
            "input_text": record.input_text,
            "sentiment_label": record.sentiment_label,
            "confidence": record.confidence,
            "model_used": record.model_used,
            "cost": record.cost,
            "trigger_reason": record.trigger_reason,
            "action": record.action,
            "notes": record.notes,
            "timestamp": (
                record.timestamp.isoformat()
                if record.timestamp
                else None
            ),
            "sequence_number": record.sequence_number,
            "previous_hash": record.previous_hash,
            "record_hash": record.record_hash,
            "archived_at": (
                record.archived_at.isoformat()
                if record.archived_at
                else None
            ),
        }
        for record in records
    ]


@router.get("/audit/verify")
def verify_sentiment_audit_chain(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """
    Verify the SHA-256 hash chain for a tenant.
    """

    audit_logger = SentimentAuditLogger(db)

    return audit_logger.verify_hash_chain(
        tenant_id=tenant_id,
    )


@router.get("/audit/export")
def export_sentiment_audit(
    tenant_id: str,
    customer_id: str | None = None,
    job_id: int | None = None,
    manager_id: str | None = None,
    sentiment_label: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    format: str = "csv",
    db: Session = Depends(get_db),
):
    """
    Export sentiment audit records as CSV or PDF.
    """

    format = format.lower()

    if format not in {"csv", "pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format. Use csv or pdf.",
        )

    records = _get_records(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        job_id=job_id,
        manager_id=manager_id,
        sentiment_label=sentiment_label,
        start_date=start_date,
        end_date=end_date,
    )

    if format == "csv":
        return _export_csv(records)

    return _export_pdf(records)


def _export_csv(records):
    output = StringIO()
    csv_writer = writer(output)

    csv_writer.writerow(
        [
            "id",
            "tenant_id",
            "event_type",
            "customer_id",
            "job_id",
            "manager_id",
            "input_text",
            "sentiment_label",
            "confidence",
            "model_used",
            "cost",
            "trigger_reason",
            "action",
            "notes",
            "timestamp",
            "sequence_number",
            "previous_hash",
            "record_hash",
            "archived_at",
        ]
    )

    for record in records:
        csv_writer.writerow(
            [
                record.id,
                record.tenant_id,
                record.event_type,
                record.customer_id,
                record.job_id,
                record.manager_id,
                record.input_text,
                record.sentiment_label,
                record.confidence,
                record.model_used,
                record.cost,
                record.trigger_reason,
                record.action,
                record.notes,
                (
                    record.timestamp.isoformat()
                    if record.timestamp
                    else None
                ),
                record.sequence_number,
                record.previous_hash,
                record.record_hash,
                (
                    record.archived_at.isoformat()
                    if record.archived_at
                    else None
                ),
            ]
        )

    output.seek(0)

    filename = (
        "sentiment_audit_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


def _export_pdf(records):
    output = BytesIO()

    pdf = canvas.Canvas(
        output,
        pagesize=landscape(A4),
    )

    width, height = landscape(A4)

    title_y = height - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(
        40,
        title_y,
        "Sentiment Audit Trail",
    )

    y = title_y - 30

    headers = [
        "ID",
        "Event",
        "Customer",
        "Job",
        "Manager",
        "Sentiment",
        "Confidence",
        "Action",
        "Timestamp",
    ]

    x_positions = [
        40,
        70,
        145,
        220,
        270,
        350,
        430,
        500,
        570,
    ]

    def draw_header():
        pdf.setFont(
            "Helvetica-Bold",
            8,
        )

        for x, header in zip(
            x_positions,
            headers,
        ):
            pdf.drawString(
                x,
                y,
                header,
            )

    draw_header()

    y -= 18

    pdf.setFont(
        "Helvetica",
        7,
    )

    for record in records:
        if y < 35:
            pdf.showPage()

            y = height - 40

            draw_header()

            y -= 18

            pdf.setFont(
                "Helvetica",
                7,
            )

        values = [
            str(record.id or ""),
            str(record.event_type or ""),
            str(record.customer_id or ""),
            str(record.job_id or ""),
            str(record.manager_id or ""),
            str(record.sentiment_label or ""),
            (
                f"{record.confidence:.3f}"
                if record.confidence is not None
                else ""
            ),
            str(record.action or ""),
            (
                record.timestamp.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if record.timestamp
                else ""
            ),
        ]

        for x, value in zip(
            x_positions,
            values,
        ):
            pdf.drawString(
                x,
                y,
                value[:25],
            )

        y -= 14

    pdf.save()

    output.seek(0)

    filename = (
        "sentiment_audit_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )