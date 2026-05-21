from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class LinguisticDriftDetector:
    def __init__(self, embed_service: Any | None = None):
        self._embed = embed_service
        self._embed_available: bool | None = None

    def _check_embed(self) -> bool:
        if self._embed_available is not None:
            return self._embed_available
        if self._embed is not None:
            self._embed_available = True
            return True
        try:
            from app.ai.embeddings import EmbeddingService
            self._embed = EmbeddingService()
            self._embed_available = True
        except Exception:
            self._embed_available = False
        return self._embed_available

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na < 1e-10 or nb < 1e-10:
            return 0.0
        return dot / (na * nb)

    def _keyword_drift_score(
        self,
        historical: list[str],
        recent: list[str],
        entity: str,
    ) -> float:
        def freq(texts: list[str]) -> float:
            total = sum(1 for t in texts if entity.lower() in t.lower())
            return total / max(len(texts), 1)
        hist_freq = freq(historical)
        rec_freq = freq(recent)
        if hist_freq < 1e-6 and rec_freq < 1e-6:
            return 0.0
        if hist_freq < 1e-6:
            return min(rec_freq * 2, 1.0)
        return (rec_freq - hist_freq) / max(hist_freq, 1e-6)

    async def compute_drift(
        self,
        historical: list[str],
        recent: list[str],
        entities: list[str],
    ) -> dict[str, dict[str, Any]]:
        scores: dict[str, dict[str, Any]] = {}
        if self._check_embed():
            try:
                all_texts = historical + recent
                embeddings = self._embed.encode(all_texts)
                h_count = len(historical)
                if len(embeddings) == len(all_texts) and h_count > 0 and len(recent) > 0:
                    h_embed = [sum(c) / len(c) for c in zip(*embeddings[:h_count])]
                    r_embed = [sum(c) / len(c) for c in zip(*embeddings[h_count:])]
                    global_drift = 1.0 - self._cosine_similarity(h_embed, r_embed)
                else:
                    global_drift = 0.0
            except Exception as exc:
                logger.warning("Embedding drift computation failed: %s", exc)
                global_drift = 0.0
        else:
            global_drift = 0.0

        for entity in entities:
            kw_drift = self._keyword_drift_score(historical, recent, entity)
            combined = max(global_drift, kw_drift)
            direction = "positive" if combined > 0.1 else "neutral" if combined > -0.1 else "negative"
            scores[entity] = {
                "drift_score": round(combined, 4),
                "keyword_score": round(kw_drift, 4),
                "global_drift": round(global_drift, 4),
                "direction": direction,
            }
        return scores


class RLMService:
    """
    Enhanced RLM service implementing dspy.RLM for recursive deep archive mining.

    Three operating modes:
      1. scan_directory  – Recursive file traversal over archives with REPL-based
         programmatic search, sub-agent spawning, and token budgeting.
      2. scan_text_batch – Programmatic search + sub-agent analysis over a loaded
         text corpus.
      3. detect_drift    – Linguistic change-point detection via embedding cosine
         similarity and keyword-frequency delta scoring.

    Uses dspy.RLM signatures, sub_lm parameter for cost-efficient recursion
    (cheap model for scanning, frontier for synthesis), and trajectory inspection
    for white-box debugging. Falls back gracefully when dspy is not installed.
    """

    def __init__(self):
        self._available: bool | None = None
        self._last_trajectory: str | None = None
        self._drift_detector = LinguisticDriftDetector()
        self._token_budget: int = 1_000_000
        self._accumulated_state: list[dict[str, Any]] = []

    # ── Availability ──────────────────────────────────────────────────────────

    def check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import dspy  # noqa: F401
            self._available = True
        except ImportError:
            logger.warning("dspy is not installed. RLMService will use fallback mode.")
            self._available = False
        return self._available

    def _consume_token_budget(self, tokens: int) -> bool:
        self._token_budget -= tokens
        return self._token_budget > 0

    def _reset_budget(self, max_tokens: int = 1_000_000) -> None:
        self._token_budget = max_tokens

    # ── DSPy.RLM helpers ─────────────────────────────────────────────────────

    def _build_rlm_module(self, signature: str, sub_lm: str):
        import dspy

        class _RLMWrapper(dspy.Module):
            def __init__(self):
                super().__init__()
                self.rlm = dspy.RLM(
                    signature=signature,
                    sub_lm=sub_lm,
                )

            def forward(self, **kwargs):
                context = kwargs.pop("context", "")
                query = kwargs.pop("query", "")
                extra = ", ".join(f"{k}={v}" for k, v in kwargs.items())
                full_query = f"{query}. Additional: {extra}" if extra else query
                return self.rlm(context=context, query=full_query)

        return _RLMWrapper()

    async def _dspy_call(
        self,
        signature: str,
        context: str,
        query: str,
        sub_lm: str = "gpt-4o-mini",
        **kwargs: Any,
    ) -> Any:
        module = self._build_rlm_module(signature, sub_lm)
        result = await asyncio.to_thread(module, context=context, query=query, **kwargs)
        try:
            import dspy
            self._last_trajectory = dspy.inspect_history() if hasattr(dspy, "inspect_history") else None
        except Exception:
            pass
        return result

    # ── Public API ────────────────────────────────────────────────────────────

    async def scan_directory(
        self,
        directory: str,
        keywords: list[str] | None = None,
        file_pattern: str = "*",
        max_tokens: int = 1_000_000,
        sub_lm: str = "gpt-4o-mini",
        spawn_sub_agents: bool = True,
        max_file_chars: int = 100_000,
    ) -> dict[str, Any]:
        self._reset_budget(max_tokens)
        self._accumulated_state = []

        if not os.path.isdir(directory):
            return {
                "alpha_vector": {"error": f"Directory not found: {directory}"},
                "token_estimate": 0,
                "files_scanned": 0,
            }

        files = self._discover_files(directory, file_pattern)
        total_tokens = 0
        scan_results: list[dict[str, Any]] = []

        for fpath in files:
            if not self._consume_token_budget(0):
                logger.info("Token budget exhausted at %d files", len(scan_results))
                break

            content = self._read_file_chunk(fpath, max_file_chars)
            if content is None:
                continue

            tokens = _estimate_tokens(content)
            total_tokens += tokens

            if keywords and not self._keyword_match(content, keywords):
                continue

            if self.check_available() and spawn_sub_agents and tokens > 50_000:
                sub_result = await self.spawn_sub_agent(
                    document=content,
                    instruction=f"Extract all alpha signals related to {keywords or 'any market pattern'}. Return structured findings.",
                    sub_lm=sub_lm,
                )
                scan_results.append({
                    "file": fpath,
                    "source_hash": self.compute_source_hash(fpath),
                    "tokens": tokens,
                    "sub_agent_extraction": sub_result,
                    "method": "sub_agent",
                })
            else:
                findings = self._extract_keyword_findings(content, keywords)
                scan_results.append({
                    "file": fpath,
                    "source_hash": self.compute_source_hash(fpath),
                    "tokens": tokens,
                    "findings": findings,
                    "method": "direct_scan",
                })

            if not self._consume_token_budget(tokens):
                break

        if self.check_available() and scan_results:
            try:
                synthesis = await self._dspy_call(
                    signature="context, query -> alpha_vector",
                    context=f"Archive scan of {directory}. Found {len(scan_results)} relevant files.",
                    query=f"Synthesize findings into a structured alpha vector. Keywords: {keywords}. Files: {[r['file'] for r in scan_results[:20]]}",
                    sub_lm="gpt-4o" if sub_lm == "gpt-4o-mini" else sub_lm,
                )
                alpha = synthesis.alpha_vector if hasattr(synthesis, "alpha_vector") else str(synthesis)
            except Exception as exc:
                logger.warning("RLM synthesis failed: %s", exc)
                alpha = self._build_alpha_from_results(scan_results)
        else:
            alpha = self._build_alpha_from_results(scan_results)

        return {
            "alpha_vector": alpha,
            "token_estimate": total_tokens,
            "files_scanned": len(files),
            "files_matched": len(scan_results),
            "budget_remaining": self._token_budget,
        }

    async def scan_text_batch(
        self,
        texts: list[str],
        query: str,
        sub_lm: str = "gpt-4o-mini",
        max_tokens: int = 500_000,
        spawn_sub_agents: bool = True,
    ) -> dict[str, Any]:
        self._reset_budget(max_tokens)
        self._accumulated_state = []

        if not texts:
            return {"alpha_vector": {}, "token_estimate": 0, "documents_processed": 0}

        total_tokens = sum(_estimate_tokens(t) for t in texts)
        filtered: list[dict[str, Any]] = []

        for i, text in enumerate(texts):
            if not self._consume_token_budget(_estimate_tokens(text)):
                break
            if spawn_sub_agents and len(text) > 20_000 and self.check_available():
                sub = await self.spawn_sub_agent(
                    document=text,
                    instruction=f"In context of query '{query[:200]}', extract all relevant alpha signals.",
                    sub_lm=sub_lm,
                )
                filtered.append({"index": i, "extraction": sub, "tokens": _estimate_tokens(text)})
            else:
                filtered.append({"index": i, "preview": text[:500], "tokens": _estimate_tokens(text)})

        if self.check_available():
            try:
                result = await self._dspy_call(
                    signature="context, query -> alpha_vector",
                    context=f"Text corpus: {len(texts)} documents, {len(filtered)} passed filter. Query: {query}",
                    query=f"Analyze {len(filtered)} text segments. Extract alpha signals, sentiment shifts, and structural patterns. Return structured alpha_vector.",
                    sub_lm=sub_lm,
                )
                alpha = result.alpha_vector if hasattr(result, "alpha_vector") else str(result)
            except Exception as exc:
                logger.warning("RLM text batch failed: %s", exc)
                alpha = {"filtered_count": len(filtered), "query": query[:200], "note": "fallback - no dspy synthesis"}
        else:
            alpha = {"filtered_count": len(filtered), "query": query[:200]}

        return {
            "alpha_vector": alpha,
            "token_estimate": total_tokens,
            "documents_processed": len(texts),
            "documents_filtered": len(filtered),
        }

    async def detect_linguistic_drift(
        self,
        texts_historical: list[str],
        texts_recent: list[str],
        target_entities: list[str],
        use_dspy: bool = True,
        sub_lm: str = "gpt-4o-mini",
    ) -> dict[str, Any]:
        drift_scores = await self._drift_detector.compute_drift(
            historical=texts_historical,
            recent=texts_recent,
            entities=target_entities,
        )

        if self.check_available() and use_dspy:
            try:
                dspy_result = await self._dspy_call(
                    signature="historical, recent, entities -> drift_report",
                    context=f"Historical ({len(texts_historical)} docs): {str(texts_historical[:3000])}",
                    query=f"Recent ({len(texts_recent)} docs): {str(texts_recent[:3000])}. Entities: {target_entities}. Detect semantic drift.",
                    sub_lm=sub_lm,
                )
                dspy_drift = dspy_result.drift_report if hasattr(dspy_result, "drift_report") else {}
                for entity in target_entities:
                    if entity not in drift_scores:
                        drift_scores[entity] = {"drift_score": 0.0, "direction": "neutral"}
                    if isinstance(dspy_drift, dict) and entity in dspy_drift:
                        dspy_val = dspy_drift[entity]
                        if isinstance(dspy_val, (int, float)):
                            drift_scores[entity]["dspy_drift"] = dspy_val
                        elif isinstance(dspy_val, dict):
                            drift_scores[entity].update(dspy_val)
            except Exception as exc:
                logger.warning("DSPy drift detection failed, using embedding-only: %s", exc)

        entities_with_drift = [e for e, s in drift_scores.items() if abs(s.get("drift_score", 0)) > 0.05]
        top_drift = sorted(entities_with_drift, key=lambda e: abs(drift_scores[e]["drift_score"]), reverse=True)[:5]

        return {
            "drift_scores": drift_scores,
            "top_drift_entities": top_drift,
            "total_entities_analyzed": len(target_entities),
            "historical_docs": len(texts_historical),
            "recent_docs": len(texts_recent),
            "method": "embedding+dspy" if (self.check_available() and use_dspy) else "embedding",
        }

    async def spawn_sub_agent(
        self,
        document: str,
        instruction: str,
        sub_lm: str = "gpt-4o-mini",
        max_depth: int = 3,
        depth: int = 0,
    ) -> str:
        if depth >= max_depth:
            return f"[max depth {max_depth} reached]"

        if not self.check_available():
            preview = document[:2000]
            kw = re.findall(r'\b\w+\b', instruction)
            matches = [kw for kw in kw if kw.lower() in preview.lower()]
            return f"Fallback sub-agent: doc={len(document)} chars, instruction='{instruction[:100]}', keyword_matches={matches[:10]}"

        try:
            chunk_size = len(document) // min(max_depth, max(1, len(document) // 20_000 + 1))
            if len(document) > 50_000 and depth < max_depth - 1:
                chunks = [document[i:i + chunk_size] for i in range(0, len(document), chunk_size)]
                sub_results = []
                for i, chunk in enumerate(chunks[:5]):
                    sub = await self.spawn_sub_agent(
                        document=chunk,
                        instruction=instruction,
                        sub_lm=sub_lm,
                        max_depth=max_depth,
                        depth=depth + 1,
                    )
                    sub_results.append(f"[Chunk {i}]: {sub}")
                combined = "\n".join(sub_results)

                result = await self._dspy_call(
                    signature="document, instruction -> extraction",
                    context=f"Sub-agent results from {len(sub_results)} chunks of larger document.",
                    query=f"Synthesize sub-agent extractions: {combined[:5000]}. Instruction: {instruction[:500]}",
                    sub_lm=sub_lm,
                )
                if hasattr(result, "extraction"):
                    return result.extraction
                return str(result)
            else:
                result = await self._dspy_call(
                    signature="document, instruction -> extraction",
                    context=document[:30_000],
                    query=f"Extract alpha signals. Instruction: {instruction[:500]}",
                    sub_lm=sub_lm,
                )
                if hasattr(result, "extraction"):
                    return result.extraction
                return str(result)

        except Exception as exc:
            logger.warning("Sub-agent failed at depth %d: %s", depth, exc)
            return f"[error: {exc}]"

    async def run_pipeline(
        self,
        directory: str,
        keywords: list[str] | None = None,
        historical_texts: list[str] | None = None,
        recent_texts: list[str] | None = None,
        entities: list[str] | None = None,
        max_tokens: int = 1_000_000,
        sub_lm: str = "gpt-4o-mini",
    ) -> dict[str, Any]:
        """
        Full RLM pipeline: archive scan → alpha vector → drift detection.

        Matches the Phase 0 pipeline from the PRD:
          Input: Massive archives (audits, filings, forums, news)
          Process: Recursive REPL → programmatic filter → sub-agent analysis → pattern detection
          Output: Structured Alpha Vector
        """
        scan_result = await self.scan_directory(
            directory=directory,
            keywords=keywords,
            max_tokens=max_tokens // 2,
            sub_lm=sub_lm,
        )

        drift_result = None
        if historical_texts and recent_texts and entities:
            drift_result = await self.detect_linguistic_drift(
                texts_historical=historical_texts,
                texts_recent=recent_texts,
                target_entities=entities,
                sub_lm=sub_lm,
            )

        alpha = scan_result.get("alpha_vector", {})

        if drift_result and drift_result.get("top_drift_entities"):
            if isinstance(alpha, dict):
                alpha["drift_signals"] = {
                    e: drift_result["drift_scores"].get(e, {})
                    for e in drift_result["top_drift_entities"]
                }

        return {
            "alpha_vector": alpha,
            "scan": {
                "token_estimate": scan_result.get("token_estimate", 0),
                "files_scanned": scan_result.get("files_scanned", 0),
                "files_matched": scan_result.get("files_matched", 0),
            },
            "drift": drift_result,
            "pipeline_complete": True,
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _discover_files(self, directory: str, pattern: str) -> list[str]:
        import fnmatch
        files = []
        for root, _dirs, fnames in os.walk(directory):
            for fname in fnames:
                if fnmatch.fnmatch(fname, pattern):
                    files.append(os.path.join(root, fname))
        return sorted(files)

    def _read_file_chunk(self, fpath: str, max_chars: int = 100_000) -> str | None:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars)
        except Exception:
            return None

    def _keyword_match(self, content: str, keywords: list[str]) -> bool:
        content_lower = content.lower()
        return any(kw.lower() in content_lower for kw in keywords)

    def _extract_keyword_findings(
        self,
        content: str,
        keywords: list[str] | None,
    ) -> list[dict[str, Any]]:
        if not keywords:
            return [{"snippet": content[:500], "keyword": "any"}]
        findings = []
        content_lower = content.lower()
        for kw in keywords:
            idx = content_lower.find(kw.lower())
            if idx != -1:
                start = max(0, idx - 100)
                end = min(len(content), idx + len(kw) + 200)
                findings.append({
                    "keyword": kw,
                    "snippet": content[start:end],
                    "position": idx,
                })
        return findings

    def _build_alpha_from_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        findings = []
        for r in results:
            if r.get("method") == "sub_agent":
                findings.append({
                    "file": r["file"],
                    "source_hash": r.get("source_hash"),
                    "extraction": r.get("sub_agent_extraction", ""),
                })
            else:
                findings.extend(r.get("findings", []))
        return {
            "findings": findings,
            "total_files_with_signals": len(results),
            "accumulated_state": self._accumulated_state,
        }

    # ── Utility ───────────────────────────────────────────────────────────────

    def inspect_last_trajectory(self) -> str | None:
        return self._last_trajectory

    def compute_source_hash(self, source_path: str) -> str:
        return hashlib.sha256(source_path.encode()).hexdigest()

    def get_accumulated_state(self) -> list[dict[str, Any]]:
        return list(self._accumulated_state)

    async def fallback_scan_directory(
        self,
        directory: str,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        return await self._fallback_scan(directory, keywords)

    async def _fallback_scan(self, directory: str, keywords: list[str] | None = None) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        total_files = 0
        for root, _dirs, files in os.walk(directory):
            for fname in files:
                total_files += 1
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(50000)
                    if keywords:
                        for kw in keywords:
                            if kw.lower() in content.lower():
                                findings.append({"file": fpath, "keyword": kw, "snippet": content[:500]})
                                break
                except Exception:
                    continue
        return {
            "alpha_vector": {"findings": findings, "total_files_scanned": total_files},
            "token_estimate": 0,
            "files_scanned": total_files,
            "files_matched": len(findings),
        }
