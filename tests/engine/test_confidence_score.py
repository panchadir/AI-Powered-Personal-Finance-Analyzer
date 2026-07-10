"""Confidence Score engine tests (Story 4.4 → S4.3/S4.4, FR-5, AD-9).

Asserts the CS-1..CS-4 companion contract (contract §6) that the Safe-to-Spend suite
(Story 4.3) left to this story: CS-1 score ordering and CS-3 event binding. CS-2
(prediction confidence) and CS-4 (no contradiction via STS) are re-checked here from the
score side. Deterministic, zero LLM calls (AD-1, enforced by ``conftest.py``).

Evidence packs are produced by the real ``compute_safe_to_spend`` on the locked scenario
inputs (reused from ``test_scenarios.py``) so score and Safe-to-Spend can never diverge.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from services.engine.confidence_score import ScoreResult, compute_confidence_score
from services.engine.safe_to_spend import compute_safe_to_spend

from tests.engine.test_scenarios import CASES

D = Decimal


def _evidence(case_name: str):
    ei = next(c.ei for c in CASES if c.name == case_name)
    return compute_safe_to_spend(ei)


def _score(case_name: str, **kwargs) -> ScoreResult:
    return compute_confidence_score(_evidence(case_name), **kwargs)


# ------------------------------------------------------------------- CS-1: preparedness ordering


class TestCS1Ordering:
    def test_comfortable_scores_above_tight_but_covered(self) -> None:
        # S1 (bal 42k, pool 25k) must score above S6 (bal 30k, pool 3.7k).
        assert _score("s1_healthy_mid_cycle").score > _score("s6_collision").score

    def test_shortfall_scores_lowest(self) -> None:
        s1 = _score("s1_healthy_mid_cycle").score
        s6 = _score("s6_collision").score
        s10 = _score("s10_shortfall").score
        assert s10 < s6 < s1  # shortfall strictly lowest of the three

    def test_no_commitments_scores_high(self) -> None:
        # S11 (all headroom) should be at/near the top of the covered band.
        assert _score("s11_over_conservatism_guard").score >= _score("s1_healthy_mid_cycle").score


class TestScoreBounds:
    @pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
    def test_score_within_0_100(self, case) -> None:
        result = compute_confidence_score(compute_safe_to_spend(case.ei))
        assert 0 <= result.score <= 100

    def test_shortfall_in_lowest_band(self) -> None:
        assert _score("s10_shortfall").score <= 20


# ------------------------------------------------------------------- CS-3: event binding (AD-9)


class TestCS3EventBinding:
    @pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
    def test_every_result_carries_explanation_and_action(self, case) -> None:
        result = compute_confidence_score(
            compute_safe_to_spend(case.ei), trigger_event="statement_upload"
        )
        assert result.trigger_event == "statement_upload"
        assert result.explanation.strip() != ""
        assert result.suggested_action.strip() != ""

    def test_delta_from_no_previous_equals_score(self) -> None:
        result = _score("s1_healthy_mid_cycle", previous_score=None)
        assert result.delta == result.score

    def test_delta_from_previous_score(self) -> None:
        result = _score("s1_healthy_mid_cycle", previous_score=50)
        assert result.delta == result.score - 50

    def test_field_names_match_score_event_model(self) -> None:
        # CS-3: exact spelling for the deferred writeback (trigger_event / suggested_action).
        result = _score("s1_healthy_mid_cycle")
        assert hasattr(result, "trigger_event") and not hasattr(result, "triggering_event")
        assert hasattr(result, "suggested_action") and not hasattr(result, "action")


# ------------------------------------------------------------------- CS-4: no contradiction


class TestCS4NoContradiction:
    def test_shortfall_low_score_and_honest_explanation(self) -> None:
        evidence = _evidence("s10_shortfall")
        result = compute_confidence_score(evidence)
        # Never "well prepared" while Safe-to-Spend is ₹0.
        assert evidence.safe_to_spend_today == D("0")
        assert result.score <= 20
        assert "exceed" in result.explanation.lower()


# ------------------------------------------------------- CS-2 pass-through + cold start (FR-5.2/5.4)


class TestPredictionConfidenceAndColdStart:
    def test_prediction_confidence_passed_through_not_conflated(self) -> None:
        evidence = _evidence("s4_variable_top_of_range")
        result = compute_confidence_score(evidence)
        assert result.prediction_confidence == evidence.prediction_confidence == "Medium"

    def test_cold_start_computes_real_score_with_low_confidence(self) -> None:
        # S7 (low_data): real computed score, NOT a fake neutral-50; prediction confidence Low.
        result = _score("s7_cold_start_low_confidence")
        assert result.prediction_confidence == "Low"
        assert 0 < result.score <= 100
        assert result.score != 50  # no fake neutral default (FR-5.4)
