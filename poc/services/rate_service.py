from datetime import date, timedelta

from sqlalchemy.orm import Session

from poc.db_models import Rate, _uuid, _utcnow
from poc.schemas import RateCreate, RateLookupRequest, RateLookupResponse, RateResponse, RateUpdate


def create_rate(db: Session, data: RateCreate) -> Rate:
    rate = Rate(id=_uuid(), **data.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


def get_rate(db: Session, rate_id: str) -> Rate | None:
    return db.query(Rate).filter(Rate.id == rate_id).first()


def list_rates(
    db: Session,
    mode: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    status: str | None = None,
) -> list[Rate]:
    q = db.query(Rate)
    if mode:
        q = q.filter(Rate.mode == mode.upper())
    if origin:
        q = q.filter(Rate.origin_port == origin.upper())
    if destination:
        q = q.filter(Rate.destination_port == destination.upper())
    if status:
        q = q.filter(Rate.status == status.upper())
    return q.order_by(Rate.created_at.desc()).all()


def update_rate(db: Session, rate_id: str, data: RateUpdate) -> Rate | None:
    rate = get_rate(db, rate_id)
    if not rate:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)
    rate.updated_at = _utcnow()
    db.commit()
    db.refresh(rate)
    return rate


def expire_stale_rates(db: Session) -> int:
    today = date.today()
    stale = db.query(Rate).filter(Rate.status == "ACTIVE", Rate.valid_to < today).all()
    for r in stale:
        r.status = "EXPIRED"
    db.commit()
    return len(stale)


def lookup_rate(db: Session, req: RateLookupRequest) -> RateLookupResponse:
    """Cascade rate lookup: EXACT → SIMILAR → EXPIRED → NONE."""
    today = date.today()
    origin = req.origin.upper()
    dest = req.destination.upper()
    mode = req.mode.upper()

    # 1. EXACT match
    exact = (
        db.query(Rate)
        .filter(
            Rate.origin_port == origin,
            Rate.destination_port == dest,
            Rate.mode == mode,
            Rate.status == "ACTIVE",
            Rate.valid_to >= today,
        )
        .order_by(Rate.valid_to.desc())
        .first()
    )
    if exact:
        cost = _estimate_cost(exact, req.weight_kg, req.is_dangerous_goods)
        return RateLookupResponse(
            found=True,
            match_type="EXACT",
            rate=RateResponse.model_validate(exact),
            estimated_cost=cost,
            confidence=0.95,
            message=f"Exact rate found: {exact.carrier_name} {origin}→{dest}",
        )

    # 2. SIMILAR — same destination + mode, different origin
    similar = (
        db.query(Rate)
        .filter(
            Rate.destination_port == dest,
            Rate.mode == mode,
            Rate.status == "ACTIVE",
            Rate.valid_to >= today,
        )
        .order_by(Rate.valid_to.desc())
        .first()
    )
    if similar:
        cost = _estimate_cost(similar, req.weight_kg, req.is_dangerous_goods)
        return RateLookupResponse(
            found=True,
            match_type="SIMILAR",
            rate=RateResponse.model_validate(similar),
            estimated_cost=cost,
            confidence=0.6,
            message=f"Similar route found: {similar.carrier_name} {similar.origin_port}→{dest} (requested {origin}→{dest})",
        )

    # 3. EXPIRED — same route but expired within last 30 days
    cutoff = today - timedelta(days=30)
    expired = (
        db.query(Rate)
        .filter(
            Rate.origin_port == origin,
            Rate.destination_port == dest,
            Rate.mode == mode,
            Rate.valid_to >= cutoff,
            Rate.valid_to < today,
        )
        .order_by(Rate.valid_to.desc())
        .first()
    )
    if expired:
        cost = _estimate_cost(expired, req.weight_kg, req.is_dangerous_goods)
        return RateLookupResponse(
            found=True,
            match_type="EXPIRED",
            rate=RateResponse.model_validate(expired),
            estimated_cost=cost,
            confidence=0.2,
            message=f"Expired rate found (valid until {expired.valid_to}): {expired.carrier_name} {origin}→{dest}",
        )

    # 4. NONE
    return RateLookupResponse(
        found=False,
        match_type="NONE",
        confidence=0.0,
        message=f"No rates found for {origin}→{dest} ({mode})",
    )


def _estimate_cost(rate: Rate, weight_kg: float | None, is_dg: bool) -> float | None:
    if weight_kg is None:
        return None
    base = rate.rate_per_unit * weight_kg
    if rate.minimum_charge and base < rate.minimum_charge:
        base = rate.minimum_charge
    if is_dg and rate.dg_surcharge_pct:
        base *= 1 + rate.dg_surcharge_pct / 100
    return round(base, 2)
