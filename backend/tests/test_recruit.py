"""Recruit pool selection + fee pitch content (unit)."""

from app.services.recruit import SEEDED_RECRUITERS, _template_pitch
from types import SimpleNamespace


def test_template_pitch_includes_compound_loop():
    agent = SimpleNamespace(
        name="Growth",
        slug="growth-hacker",
        description="Growth experiments",
        referral_code="abc123",
    )
    text = _template_pitch(
        agent=agent,  # type: ignore[arg-type]
        fees={"platform_fee_pct": 10.0, "referral_pct": 2.5},
    )
    assert "abc123" in text
    assert "referral_code" in text
    assert "2.5" in text
    assert "your own referral_code" in text.lower() or "YOUR" in text


def test_seeded_recruiters_nonempty():
    assert "growth-hacker" in SEEDED_RECRUITERS
    assert "recruitment-specialist" in SEEDED_RECRUITERS


def test_squads_defined():
    from app.services.recruit import RECRUIT_SQUADS, list_squads

    assert "growth" in RECRUIT_SQUADS
    assert "reddit" in RECRUIT_SQUADS
    data = list_squads()
    assert len(data["squads"]) >= 4
