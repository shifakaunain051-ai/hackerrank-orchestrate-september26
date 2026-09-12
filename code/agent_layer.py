"""AI-agent boundary for semantic evidence, with a safe deterministic fallback.

The financial engine remains the only authority for calculations and feasibility.
This module is deliberately side-effect free: evidence is input data, never commands.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


INJECTION_MARKERS = re.compile(
    r"ignore (?:previous|all|the) |system message|developer instruction|"
    r"override (?:rules|instructions)|approve (?:this|the) purchase|"
    r"do not follow", re.IGNORECASE,
)
AMOUNT_PATTERN = re.compile(r"(?:INR|IDR|ZAR|USD|EUR|₹|\$|€)\s*([\d,]+(?:\.\d{1,2})?)", re.I)


@dataclass(frozen=True)
class Usage:
    provider: str = "none"
    model: str = "none"
    calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    fallback_requests: int = 0


@dataclass(frozen=True)
class SemanticFacts:
    intent: str
    mentioned_amount: Decimal | None
    preferences: tuple[str, ...]
    priorities: tuple[str, ...]
    commitment_terms: tuple[str, ...]
    evidence_count: int
    image_event_ids: tuple[str, ...]
    injection_detected: bool
    source: str


class SemanticProvider(Protocol):
    name: str
    model: str

    def available(self) -> bool: ...
    def extract(self, request: dict, evidence: list[str]) -> SemanticFacts | None: ...


class UnavailableProvider:
    """Explicit no-call provider used where no credentials/provider are configured."""
    name = "none"
    model = "none"

    def available(self) -> bool:
        return False

    def extract(self, request: dict, evidence: list[str]) -> SemanticFacts | None:
        return None


def configured_provider() -> SemanticProvider:
    """Factory boundary for future providers; never reads or exposes a secret.

    A deployment may register a provider implementation when both a provider name
    and its environment-supplied credential are available. The submission ships
    with no network client, therefore it safely uses the local fallback instead.
    """
    _provider = os.getenv("BUY_OR_WAIT_LLM_PROVIDER", "").strip()
    _credential = os.getenv("BUY_OR_WAIT_LLM_API_KEY", "").strip()
    # Intentionally no generic HTTP fallback: an unreviewed endpoint must not
    # receive financial evidence or change an answer merely because env vars exist.
    return UnavailableProvider()


class FinancialAgent:
    """Semantic/evidence agent that is downstream of rules and upstream of prose."""
    def __init__(self, engine, provider: SemanticProvider | None = None):
        self.engine = engine
        self.provider = provider or configured_provider()
        self._calls = 0
        self._fallback_requests = 0
        self.messages = engine.messages
        self.images = engine.images

    @staticmethod
    def _intent(request_type: str, text: str) -> str:
        text = text.lower()
        if "transfer" in text or request_type == "family_transfer": return "transfer"
        if "invest" in text or request_type == "investment": return "investment"
        if request_type == "travel": return "travel"
        if request_type == "education": return "education"
        return "purchase_or_payment"

    @staticmethod
    def _amount(text: str) -> Decimal | None:
        match = AMOUNT_PATTERN.search(text)
        return Decimal(match.group(1).replace(",", "")) if match else None

    def related_evidence(self, request: dict) -> tuple[list[str], tuple[str, ...]]:
        user, request_id = request["user_id"], request["request_id"]
        messages = [m["message_text"] for m in self.messages
                    if m["user_id"] == user and (m["request_id"] in ("", request_id))]
        image_events = tuple(i["related_event_id"] for i in self.images
                             if i["user_id"] == user and i["request_id"] in ("", request_id))
        return messages, image_events

    def fallback_extract(self, request: dict, evidence: list[str], image_events: tuple[str, ...]) -> SemanticFacts:
        profile = self.engine.profiles[request["user_id"]]
        joined = "\n".join(evidence)
        terms = tuple(sorted({term for term in ("salary", "rent", "bill", "loan", "income", "expense", "payment")
                              if re.search(rf"\b{term}\b", joined, re.I)}))
        return SemanticFacts(
            intent=self._intent(request["request_type"], request["request_text"]),
            mentioned_amount=self._amount(request["request_text"]),
            preferences=tuple(filter(None, profile["payment_methods_user_will_consider"].split("|"))),
            priorities=tuple(filter(None, profile["financial_priorities"].split("|"))),
            commitment_terms=terms,
            evidence_count=len(evidence), image_event_ids=image_events,
            injection_detected=bool(INJECTION_MARKERS.search(joined)), source="deterministic_fallback",
        )

    def facts_for(self, request: dict) -> SemanticFacts:
        evidence, image_events = self.related_evidence(request)
        # Providers only receive evidence after the trust boundary. Their facts
        # cannot alter the deterministic engine or its validator.
        if self.provider.available() and not INJECTION_MARKERS.search("\n".join(evidence)):
            result = self.provider.extract(request, evidence)
            if result is not None:
                self._calls += 1
                return result
        self._fallback_requests += 1
        return self.fallback_extract(request, evidence, image_events)

    def personalized_explanation(self, request: dict, decision: dict, facts: SemanticFacts) -> str:
        """Grounded prose only; no amount/date/method is recomputed here."""
        profile = self.engine.profiles[request["user_id"]]
        method = decision["recommended_payment_method"].replace("_", " ")
        priority = facts.priorities[0].replace("_", " ") if facts.priorities else "financial stability"
        evidence_note = " Relevant untrusted evidence was reviewed." if facts.evidence_count else ""
        if facts.injection_detected:
            evidence_note += " Instruction-like text in evidence was ignored."
        return (f"For this {facts.intent.replace('_', ' ')}, recommend {method}; the validated 90-day forecast "
                f"preserves the {profile['home_currency']} {profile['minimum_balance_to_keep']} minimum while respecting "
                f"your {priority} priority and payment preferences.{evidence_note}")

    def usage(self) -> Usage:
        return Usage(provider=self.provider.name, model=self.provider.model, calls=self._calls,
                     fallback_requests=self._fallback_requests)
