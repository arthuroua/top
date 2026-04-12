from sqlalchemy.orm import Session

from app.models import AdvisorReport
from app.schemas import AdvisorReportCreate


def create_report(db: Session, payload: AdvisorReportCreate) -> AdvisorReport:
    report = AdvisorReport(
        vin=payload.vin.upper(),
        assumptions_json=payload.assumptions.model_dump(),
        result_json=payload.result.model_dump(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_id(db: Session, report_id: str) -> AdvisorReport | None:
    return db.get(AdvisorReport, report_id)
