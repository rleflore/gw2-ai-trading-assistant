"""Pydantic models for RAG pipeline structured output.

The LLM must produce JSON matching these schemas. Pydantic validates
the response and gives us type-safe objects to work with downstream.
"""
from pydantic import BaseModel, Field
from typing import Literal

class TradingSignal(BaseModel):
    affected_items: list[str]
    direction: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    time_horizon: str
    source_documents: list[str]
    expected_move_pct: float | None = None


class PipelineOutput(BaseModel):
    signals: list[TradingSignal]
    analysis_summary: str
    timestamp: str
