from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from poc.database import get_db
from poc.schemas import RateCreate, RateLookupRequest, RateLookupResponse, RateResponse, RateUpdate
from poc.services import rate_service

router = APIRouter(prefix="/api/rates", tags=["rates"])


@router.post("", response_model=RateResponse, status_code=201)
def create_rate(data: RateCreate, db: Session = Depends(get_db)):
    rate = rate_service.create_rate(db, data)
    return rate


@router.get("", response_model=list[RateResponse])
def list_rates(
    mode: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return rate_service.list_rates(db, mode=mode, origin=origin, destination=destination, status=status)


@router.get("/{rate_id}", response_model=RateResponse)
def get_rate(rate_id: str, db: Session = Depends(get_db)):
    rate = rate_service.get_rate(db, rate_id)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    return rate


@router.patch("/{rate_id}", response_model=RateResponse)
def update_rate(rate_id: str, data: RateUpdate, db: Session = Depends(get_db)):
    rate = rate_service.update_rate(db, rate_id, data)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    return rate


@router.post("/lookup", response_model=RateLookupResponse)
def lookup_rate(data: RateLookupRequest, db: Session = Depends(get_db)):
    return rate_service.lookup_rate(db, data)
