"""Fee + referral split math. All Decimal / numeric(24,6) — never float."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANT = Decimal("0.000001")
BPS = Decimal("10000")


def money(value: str | int | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class FeeRates:
    platform_fee_bps: int = 1000  # 10.00%
    referral_bps: int = 250  # 2.50% of gross (from fee pot)

    def __post_init__(self) -> None:
        if self.platform_fee_bps < 0 or self.referral_bps < 0:
            raise ValueError("bps must be non-negative")
        if self.referral_bps > self.platform_fee_bps:
            raise ValueError("referral_bps cannot exceed platform_fee_bps")


@dataclass(frozen=True)
class FeeSplit:
    gross_usdc: Decimal
    platform_fee_usdc: Decimal
    referral_usdc: Decimal
    platform_keep_usdc: Decimal
    seller_net_usdc: Decimal
    has_referrer: bool


DEFAULT_RATES = FeeRates()


def compute_split(
    gross: str | int | Decimal,
    *,
    has_referrer: bool,
    rates: FeeRates = DEFAULT_RATES,
) -> FeeSplit:
    """Single formula used by settlement and previews."""
    g = money(gross)
    if g < 0:
        raise ValueError("gross must be >= 0")

    fee = money(g * Decimal(rates.platform_fee_bps) / BPS)
    referral = money(g * Decimal(rates.referral_bps) / BPS) if has_referrer else money(0)
    if referral > fee:
        referral = fee
    platform_keep = money(fee - referral)
    seller_net = money(g - fee)
    # Invariant: gross == seller_net + platform_keep + referral
    assert seller_net + platform_keep + referral == g
    return FeeSplit(
        gross_usdc=g,
        platform_fee_usdc=fee,
        referral_usdc=referral,
        platform_keep_usdc=platform_keep,
        seller_net_usdc=seller_net,
        has_referrer=has_referrer,
    )
