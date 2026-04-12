from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.reports import create_report, get_report_by_id
from app.schemas import AdvisorReportCreate, AdvisorReportRead

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _to_read_model(record) -> AdvisorReportRead:
    return AdvisorReportRead(
        id=record.id,
        vin=record.vin,
        assumptions=record.assumptions_json,
        result=record.result_json,
        created_at=record.created_at,
    )


@router.post("", response_model=AdvisorReportRead)
def create(payload: AdvisorReportCreate, db: Session = Depends(get_db)) -> AdvisorReportRead:
    report = create_report(db, payload)
    return _to_read_model(report)


@router.get("/{report_id}", response_model=AdvisorReportRead)
def get(report_id: str, db: Session = Depends(get_db)) -> AdvisorReportRead:
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_read_model(report)
