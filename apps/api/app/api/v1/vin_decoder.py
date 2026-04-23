from fastapi import APIRouter, Query

from app.schemas import VinDecodeResponse
from app.services.vin_decoder import decode_vin

router = APIRouter(prefix="/api/v1", tags=["vin-decoder"])


@router.get("/vin-decoder/{vin}", response_model=VinDecodeResponse)
def get_vin_decode(vin: str, model_year: int | None = Query(default=None, ge=1900, le=2100)) -> VinDecodeResponse:
    return decode_vin(vin.strip().upper(), model_year)
