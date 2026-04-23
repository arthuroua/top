from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.reports import (
    create_report,
    create_report_share,
    get_active_share_for_report,
    get_pipeline_state,
    get_report_by_id,
    get_share_by_token,
    list_reports,
    set_pipeline_state,
)
from app.schemas import (
    AdvisorReportCreate,
    AdvisorReportRead,
    AdvisorReportShareCreate,
    AdvisorReportShareRead,
    ReportPipelineRead,
    ReportPipelineUpdate,
    SharedAdvisorReportRead,
)
from app.services.pdf_report import build_report_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _to_pipeline_model(record) -> ReportPipelineRead | None:
    if record is None:
        return None
    return ReportPipelineRead(
        report_id=record.report_id,
        stage=record.stage,
        note=record.note,
        updated_at=record.updated_at,
    )


def _to_read_model(record) -> AdvisorReportRead:
    return AdvisorReportRead(
        id=record.id,
        vin=record.vin,
        assumptions=record.assumptions_json,
        result=record.result_json,
        created_at=record.created_at,
        pipeline=_to_pipeline_model(record.pipeline_state),
    )


def _to_share_model(record) -> AdvisorReportShareRead:
    return AdvisorReportShareRead(
        id=record.id,
        report_id=record.report_id,
        token=record.token,
        created_at=record.created_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )


@router.post("", response_model=AdvisorReportRead)
def create(payload: AdvisorReportCreate, db: Session = Depends(get_db)) -> AdvisorReportRead:
    report = create_report(db, payload)
    return _to_read_model(report)


@router.get("", response_model=list[AdvisorReportRead])
def list_all(
    vin: str | None = Query(default=None, min_length=17, max_length=17),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AdvisorReportRead]:
    reports = list_reports(db, vin=vin.upper() if vin else None, limit=limit)
    return [_to_read_model(report) for report in reports]


@router.get("/shared/{token}", response_model=SharedAdvisorReportRead)
def get_shared(token: str, db: Session = Depends(get_db)) -> SharedAdvisorReportRead:
    share = get_share_by_token(db, token)
    if not share:
        raise HTTPException(status_code=404, detail="Shared report not found")

    report = get_report_by_id(db, share.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Shared report not found")

    return SharedAdvisorReportRead(share=_to_share_model(share), report=_to_read_model(report))


@router.get("/{report_id}/share", response_model=AdvisorReportShareRead)
def get_active_share(report_id: str, db: Session = Depends(get_db)) -> AdvisorReportShareRead:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    share = get_active_share_for_report(db, report_id)
    if not share:
        raise HTTPException(status_code=404, detail="No active share token")

    return _to_share_model(share)


@router.post("/{report_id}/share", response_model=AdvisorReportShareRead)
def create_share(
    report_id: str,
    payload: AdvisorReportShareCreate | None = None,
    db: Session = Depends(get_db),
) -> AdvisorReportShareRead:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    expires_in_days = payload.expires_in_days if payload else 30
    expires_at = None
    if expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    share = create_report_share(db, report_id=report_id, expires_at=expires_at)
    return _to_share_model(share)


@router.get("/{report_id}/pipeline", response_model=ReportPipelineRead)
def get_pipeline(report_id: str, db: Session = Depends(get_db)) -> ReportPipelineRead:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    state = get_pipeline_state(db, report_id)
    if state is None:
        state = set_pipeline_state(db, report_id=report_id, stage="lead", note=None)
    return _to_pipeline_model(state)


@router.put("/{report_id}/pipeline", response_model=ReportPipelineRead)
def update_pipeline(
    report_id: str,
    payload: ReportPipelineUpdate,
    db: Session = Depends(get_db),
) -> ReportPipelineRead:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    state = set_pipeline_state(
        db,
        report_id=report_id,
        stage=payload.stage,
        note=payload.note,
    )
    return _to_pipeline_model(state)


@router.get("/{report_id}", response_model=AdvisorReportRead)
def get(report_id: str, db: Session = Depends(get_db)) -> AdvisorReportRead:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_read_model(report)


@router.get("/{report_id}/pdf")
def get_pdf(report_id: str, db: Session = Depends(get_db)) -> Response:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    read_model = _to_read_model(report)
    pdf_bytes = build_report_pdf(read_model)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="advisor-report-{report_id}.pdf"'
        },
    )
