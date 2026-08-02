from app.services.fees import FeeRates, compute_split


def test_option_a_prime_split_with_referrer():
    s = compute_split("10.000000", has_referrer=True)
    assert str(s.platform_fee_usdc) == "1.000000"
    assert str(s.referral_usdc) == "0.250000"
    assert str(s.platform_keep_usdc) == "0.750000"
    assert str(s.seller_net_usdc) == "9.000000"
    assert s.seller_net_usdc + s.platform_keep_usdc + s.referral_usdc == s.gross_usdc


def test_split_without_referrer_platform_keeps_full_fee():
    s = compute_split("10.000000", has_referrer=False)
    assert str(s.referral_usdc) == "0.000000"
    assert str(s.platform_keep_usdc) == "1.000000"
    assert str(s.seller_net_usdc) == "9.000000"


def test_referral_cannot_exceed_fee():
    rates = FeeRates(platform_fee_bps=1000, referral_bps=250)
    s = compute_split("1.000000", has_referrer=True, rates=rates)
    assert s.referral_usdc <= s.platform_fee_usdc
