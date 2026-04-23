from __future__ import annotations

from app.schemas import LandedCostInput, LandedCostOutput

FORMULA_VERSION = "market.v1"


def _estimate_auction_fee(provider: str, bid_price_usd: float) -> tuple[float, str]:
    bid = max(0.0, bid_price_usd)
    if provider == "copart":
        if bid <= 1000:
            return 450.0, "copart tier <=1000"
        if bid <= 3000:
            return 600.0, "copart tier <=3000"
        if bid <= 5000:
            return 750.0, "copart tier <=5000"
        if bid <= 10000:
            return 950.0, "copart tier <=10000"
        if bid <= 15000:
            return 1200.0, "copart tier <=15000"
        return round(1200.0 + (bid - 15000.0) * 0.06, 2), "copart tier >15000"

    if provider == "iaai":
        if bid <= 1000:
            return 420.0, "iaai tier <=1000"
        if bid <= 3000:
            return 560.0, "iaai tier <=3000"
        if bid <= 5000:
            return 700.0, "iaai tier <=5000"
        if bid <= 10000:
            return 900.0, "iaai tier <=10000"
        if bid <= 15000:
            return 1100.0, "iaai tier <=15000"
        return round(1100.0 + (bid - 15000.0) * 0.055, 2), "iaai tier >15000"

    return round(max(300.0, bid * 0.05), 2), "generic 5% estimate"


def _compute_landed_total(payload: LandedCostInput, bid_price_usd: float) -> tuple[float, float, float, float, float, list[str]]:
    notes: list[str] = []

    if payload.manual_auction_fee_usd is not None:
        auction_fee = float(payload.manual_auction_fee_usd)
        notes.append("Manual auction fee override applied")
    else:
        auction_fee, fee_note = _estimate_auction_fee(payload.auction_provider, bid_price_usd)
        notes.append(f"Auction fee: {fee_note}")

    pre_tax = (
        bid_price_usd
        + auction_fee
        + payload.shipping_usd
        + payload.inland_usd
        + payload.port_usd
        + payload.broker_usd
        + payload.insurance_usd
        + payload.excise_usd
    )
    duty = round((bid_price_usd + payload.shipping_usd + payload.insurance_usd) * payload.duty_rate_percent / 100.0, 2)
    tax_base = pre_tax + duty
    vat = round(tax_base * payload.vat_rate_percent / 100.0, 2)
    landed_total = round(tax_base + vat + payload.repair_usd + payload.local_costs_usd + payload.other_usd, 2)

    return (round(auction_fee, 2), duty, vat, round(pre_tax, 2), round(tax_base, 2), notes + ["Estimated formula (not legal advice)"])


def _recommended_max_bid(payload: LandedCostInput) -> float | None:
    if payload.expected_sell_price_usd is None or payload.target_margin_usd is None:
        return None
    target_budget = payload.expected_sell_price_usd - payload.target_margin_usd
    if target_budget <= 0:
        return 0.0

    left = 0.0
    right = max(1000.0, payload.expected_sell_price_usd)
    best = 0.0
    for _ in range(32):
        mid = (left + right) / 2.0
        _auction_fee, _duty, vat, _pre_tax, tax_base, _notes = _compute_landed_total(payload, mid)
        landed_total = round(tax_base + vat + payload.repair_usd + payload.local_costs_usd + payload.other_usd, 2)
        if landed_total <= target_budget:
            best = mid
            left = mid
        else:
            right = mid
    return round(best, 2)


def calculate_landed_cost(payload: LandedCostInput) -> LandedCostOutput:
    auction_fee, duty, vat, pre_tax, tax_base, notes = _compute_landed_total(payload, payload.bid_price_usd)
    landed_total = round(tax_base + vat + payload.repair_usd + payload.local_costs_usd + payload.other_usd, 2)

    projected_margin: float | None = None
    if payload.expected_sell_price_usd is not None:
        projected_margin = round(payload.expected_sell_price_usd - landed_total, 2)

    recommended_bid = _recommended_max_bid(payload)

    return LandedCostOutput(
        formula_version=FORMULA_VERSION,
        auction_provider=payload.auction_provider,
        auction_fee_usd=auction_fee,
        duty_usd=duty,
        vat_usd=vat,
        pre_tax_total_usd=pre_tax,
        tax_base_usd=tax_base,
        landed_total_usd=landed_total,
        landed_total_uah=round(landed_total * payload.usd_to_uah, 2),
        landed_total_eur=round(landed_total * payload.usd_to_eur, 2),
        projected_margin_usd=projected_margin,
        recommended_max_bid_usd=recommended_bid,
        notes=notes,
    )
