"""Tests for cronwatch.escalation."""

from unittest.mock import MagicMock

import pytest

from cronwatch.config import AlertConfig
from cronwatch.escalation import (
    EscalationLevel,
    EscalationPolicy,
    build_escalation_alert_fn,
    parse_escalation_policy,
)


def _cfg(**kwargs) -> AlertConfig:
    defaults = dict(
        email_recipients=["ops@example.com"],
        smtp_host="localhost",
        smtp_port=25,
        smtp_user=None,
        smtp_password=None,
        use_tls=False,
        from_address="cronwatch@localhost",
    )
    defaults.update(kwargs)
    return AlertConfig(**defaults)


# ---------------------------------------------------------------------------
# EscalationPolicy.resolve
# ---------------------------------------------------------------------------

def test_resolve_returns_none_when_no_levels():
    policy = EscalationPolicy(levels=[])
    assert policy.resolve(5) is None


def test_resolve_returns_none_below_threshold():
    level = EscalationLevel(min_failures=3, alert_config=_cfg(), label="warn")
    policy = EscalationPolicy(levels=[level])
    assert policy.resolve(2) is None


def test_resolve_returns_level_at_threshold():
    level = EscalationLevel(min_failures=3, alert_config=_cfg(), label="warn")
    policy = EscalationPolicy(levels=[level])
    assert policy.resolve(3) is level


def test_resolve_returns_highest_matching_level():
    warn = EscalationLevel(min_failures=2, alert_config=_cfg(), label="warn")
    crit = EscalationLevel(min_failures=5, alert_config=_cfg(), label="critical")
    policy = EscalationPolicy(levels=[warn, crit])
    assert policy.resolve(5) is crit
    assert policy.resolve(4) is warn


# ---------------------------------------------------------------------------
# build_escalation_alert_fn
# ---------------------------------------------------------------------------

def test_no_escalation_uses_base_cfg():
    base = MagicMock(return_value=True)
    policy = EscalationPolicy(levels=[])
    fn = build_escalation_alert_fn(policy, base, get_streak=lambda _: 0)
    cfg = _cfg()
    fn("myjob", "oops", cfg)
    base.assert_called_once_with("myjob", "oops", cfg)


def test_escalation_replaces_alert_config():
    base = MagicMock(return_value=True)
    escalated_cfg = _cfg(email_recipients=["pager@example.com"])
    level = EscalationLevel(min_failures=3, alert_config=escalated_cfg, label="")
    policy = EscalationPolicy(levels=[level])
    original_cfg = _cfg()
    fn = build_escalation_alert_fn(policy, base, get_streak=lambda _: 4)
    fn("myjob", "oops", original_cfg)
    base.assert_called_once_with("myjob", "oops", escalated_cfg)


def test_escalation_prefixes_label():
    base = MagicMock(return_value=True)
    escalated_cfg = _cfg()
    level = EscalationLevel(min_failures=1, alert_config=escalated_cfg, label="critical")
    policy = EscalationPolicy(levels=[level])
    fn = build_escalation_alert_fn(policy, base, get_streak=lambda _: 3)
    fn("myjob", "something broke", _cfg())
    args = base.call_args[0]
    assert args[1].startswith("[CRITICAL]")


# ---------------------------------------------------------------------------
# parse_escalation_policy
# ---------------------------------------------------------------------------

def test_parse_escalation_policy_empty():
    policy = parse_escalation_policy([])
    assert policy.levels == []


def test_parse_escalation_policy_builds_levels():
    raw = [
        {"min_failures": 2, "label": "warn", "alert": {"email_recipients": ["a@b.com"]}},
        {"min_failures": 5, "label": "crit", "alert": {"email_recipients": ["pager@b.com"]}},
    ]
    policy = parse_escalation_policy(raw)
    assert len(policy.levels) == 2
    assert policy.levels[0].min_failures == 2
    assert policy.levels[1].label == "crit"
