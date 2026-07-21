"""Categorization: Tier-1 rules engine, Tier-2 LLM categorizer, Teach Me.

The category enum is the single source of truth in ``schema.py`` (AD-7).
Tier-1 rules engine is live (pulled forward from Epic 3 for POC).
"""
from services.categorize.rules import categorize_rules, RULES

__all__ = ["categorize_rules", "RULES"]
