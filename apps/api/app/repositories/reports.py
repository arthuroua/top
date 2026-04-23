import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AdvisorReport, AdvisorReportShare, ReportPipelineState
from app.schemas import AdvisorReportCreate, ReportPipelineStage

DEFAULT_REPORT_PIPELINE_STAGE: ReportPipelineStage = "lead"


def create_report(db: Session, payload: AdvisorReportCreate) -> AdvisorReport:
    report = AdvisorReport(
        vin=payload.vin.upper(),
        assumptions_json=payload.assumptions.model_dump(),
        result_json=payload.result.model_dump(),
    )
    pipeline = ReportPipelineState(
        report=report,
        stage=DEFAULT_REPORT_PIPELINE_STAGE,
        note=None,
    )
    db.add(report)
    db.add(pipeline)
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, vin: str | None = None, limit: int = 20) -> list[AdvisorReport]:
    query = select(AdvisorReport).options(selectinload(AdvisorReport.pipeline_state))
    if vin:
        query = query.where(AdvisorReport.vin == vin.upper())
    query = query.order_by(AdvisorReport.created_at.desc()).limit(limit)
    return list(db.execute(query).scalars().all())


def get_report_by_id(db: Session, report_id: str) -> AdvisorReport | None:
    return db.execute(
        select(AdvisorReport).options(selectinload(AdvisorReport.pipeline_state)).where(AdvisorReport.id == report_id)
    ).scalar_one_or_none()


def _generate_unique_token(db: Session) -> str:
    for _ in range(10):
        token = secrets.token_urlsafe(24)
        existing = db.execute(select(AdvisorReportShare.id).where(AdvisorReportShare.token == token)).first()
        if not existing:
            return token
    raise RuntimeError("Could not generate unique share token")


def create_report_share(
    db: Session,
    report_id: str,
    expires_at: datetime | None = None,
) -> AdvisorReportShare:
    share = AdvisorReportShare(
        report_id=report_id,
        token=_generate_unique_token(db),
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def _is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def get_active_share_for_report(db: Session, report_id: str) -> AdvisorReportShare | None:
    query = (
        select(AdvisorReportShare)
        .where(
            AdvisorReportShare.report_id == report_id,
            AdvisorReportShare.revoked_at.is_(None),
        )
        .order_by(AdvisorReportShare.created_at.desc())
    )
    shares = db.execute(query).scalars().all()
    for share in shares:
        if not _is_expired(share.expires_at):
            return share
    return None


def get_share_by_token(db: Session, token: str) -> AdvisorReportShare | None:
    share = db.execute(select(AdvisorReportShare).where(AdvisorReportShare.token == token)).scalar_one_or_none()
    if share is None:
        return None
    if share.revoked_at is not None:
        return None
    if _is_expired(share.expires_at):
        return None
    return share


def get_pipeline_state(db: Session, report_id: str) -> ReportPipelineState | None:
    return db.get(ReportPipelineState, report_id)


def set_pipeline_state(
    db: Session,
    *,
    report_id: str,
    stage: ReportPipelineStage,
    note: str | None = None,
) -> ReportPipelineState:
    state = db.get(ReportPipelineState, report_id)
    if state is None:
        state = ReportPipelineState(
            report_id=report_id,
            stage=stage,
            note=note,
        )
        db.add(state)
    else:
        state.stage = stage
        state.note = note

    db.commit()
    db.refresh(state)
    return state
