from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.models import ExtractionJob
from app.db.session import get_db
from app.schemas.schemas import FieldPatch, JobCreateText, JobOut
from app.services.extract import extract_invoice

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _now():
    return datetime.now(timezone.utc)


def _out(job: ExtractionJob) -> JobOut:
    return JobOut(
        id=job.id,
        filename=job.filename,
        doc_type=job.doc_type,
        status=job.status,
        fields=job.fields or {},
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    rows = db.query(ExtractionJob).order_by(ExtractionJob.created_at.desc()).limit(50).all()
    return [_out(j) for j in rows]


@router.post("", response_model=JobOut)
def create_job_text(body: JobCreateText, db: Session = Depends(get_db)):
    job = ExtractionJob(
        filename=body.filename or "pasted.txt",
        source_text=body.text,
        status="running",
        fields={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        doc_type, fields, _method = extract_invoice(body.text)
        job.doc_type = doc_type
        job.fields = fields
        job.status = "needs_review"
        job.error = None
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
    job.updated_at = _now()
    db.commit()
    db.refresh(job)
    return _out(job)


@router.post("/upload", response_model=JobOut)
async def create_job_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")
    if len(text.strip()) < 20:
        raise HTTPException(400, "File too short or unreadable. Use .txt for this MVP.")

    return create_job_text(
        JobCreateText(text=text, filename=file.filename or "upload.txt"),
        db,
    )


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return _out(job)


@router.patch("/{job_id}/fields/{key}", response_model=JobOut)
def patch_field(job_id: UUID, key: str, body: FieldPatch, db: Session = Depends(get_db)):
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    fields = dict(job.fields or {})
    prev = fields.get(key) or {"confidence": 1.0, "uncertain": False}
    fields[key] = {
        "value": body.value,
        "confidence": float(prev.get("confidence") or 1.0),
        "uncertain": False,
        "edited": True,
    }
    job.fields = fields
    job.updated_at = _now()
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(job, "fields")
    db.commit()
    db.refresh(job)
    return _out(job)


@router.post("/{job_id}/confirm", response_model=JobOut)
def confirm_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    job.status = "confirmed"
    job.updated_at = _now()
    db.commit()
    db.refresh(job)
    return _out(job)


@router.get("/{job_id}/export")
def export_job(job_id: UUID, format: str = "json", db: Session = Depends(get_db)):
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    flat = {k: (v or {}).get("value") for k, v in (job.fields or {}).items()}

    if format == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(flat.keys()))
        w.writeheader()
        w.writerow(flat)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="docschema-{job_id}.csv"'},
        )

    return Response(
        content=json.dumps(flat, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="docschema-{job_id}.json"'},
    )
