"""RAG Pipeline — retrieves context and generates structured trading signals.

Flow:
1. Build query from trigger event (new patch note, hourly scan, etc.)
2. Retrieve relevant docs from ChromaDB (patch notes + knowledge base + reddit)
3. Get price context (market analytics)
4. Assemble prompt: system + price context + retrieved docs + trigger
5. Call Ollama LLM
6. Parse and validate JSON output with Pydantic
7. Retry up to 3 times if validation fails
"""

import json
import logging
from datetime import datetime, timezone

import ollama

from gw2trading.rag.models import TradingSignal, PipelineOutput
from gw2trading.rag.prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE, RETRY_PROMPT
from gw2trading.rag.vectorstore import VectorStore
from gw2trading.analysis.price_context import PriceContext

logger = logging.getLogger("gw2trading.rag.pipeline")

MODEL = "llama3:8b"
TEMPERATURE = 0.3
MAX_RETRIES = 3


class RAGPipeline:
    """Orchestrates retrieval, prompt assembly, LLM call, and output parsing."""

    def __init__(self, model: str = MODEL):
        self.model = model
        self.vectorstore = VectorStore()
        self.price_context = PriceContext()

    async def generate_signals(self, trigger: str | None = None) -> PipelineOutput:
        """Main entry point. Retrieves context, calls LLM, validates output.

        Args:
            trigger: What triggered this analysis (e.g., "New patch note: ...")
                     If None, defaults to "Scheduled daily market scan"

        Returns:
            PipelineOutput with validated trading signals
        """
        if trigger is None:
            trigger = "Scheduled daily market scan"
        current_date = datetime.now(timezone.utc).isoformat()

        retrieved_docs = self._retrieve_documents(trigger)

        price_context = self.price_context.get_market_context()

        user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            current_date=current_date,
            trigger_event=trigger,
            price_context=price_context,
            retrieved_documents=retrieved_docs,
        )
        raw_response = self._call_llm(SYSTEM_PROMPT, user_prompt)

        for attempt in range(MAX_RETRIES):
            try:
                output = self._parse_response(raw_response)
                return output
            except ValueError as e:
                logger.warning(f"Attempt {attempt+1}: {e}")
                retry_prompt = RETRY_PROMPT.format(
                    schema=PipelineOutput.model_json_schema(),
                    invalid_response=raw_response,
                )
                raw_response = self._call_llm(SYSTEM_PROMPT, retry_prompt)
        raise ValueError("Failed to get valid JSON response after multiple attempts.")
    

        

    def _retrieve_documents(self, query: str) -> str:
        """Retrieve relevant documents from ChromaDB and format them as a string.
        Returns a formatted string of all retrieved documents.
        """

        primary_docs = self.vectorstore.query(query_text=query, n_results=4)
        kb_docs = self.vectorstore.query(query_text=query, n_results=2, source_type="knowledge_base")
        reddit_docs = self.vectorstore.query(query_text=query, n_results=2, source_type="reddit_post")
        all_docs = primary_docs + kb_docs + reddit_docs
        formatted_docs = []
        for doc in all_docs:
            metadata = doc.get("metadata", {})
            source = metadata.get("source_type", "unknown")
            date = metadata.get("date", "N/A")
            text = doc.get("text", "")
            formatted_docs.append(f"[Source: {source}, Date: {date}]\n{text}\n---")
        return "\n".join(formatted_docs)

        

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama LLM and return the raw response text."""

        ollama_response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": TEMPERATURE},
            format="json",
        )
        return ollama_response["message"]["content"]

        

    def _parse_response(self, raw_response: str) -> PipelineOutput:
        """Parse raw LLM JSON response into a validated PipelineOutput.

        Steps:
            1. json.loads(raw_response) to get a dict
            2. PipelineOutput(**data) to validate with Pydantic
            3. If either step fails, raise ValueError with details

        Returns validated PipelineOutput on success.
        Raises ValueError if JSON is invalid or doesn't match schema.
        """

        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e.msg}") from e

        try:
            output = PipelineOutput(**data)
        except Exception as e:
            raise ValueError(f"JSON does not match schema: {e}") from e

        return output

