# market_retrieval.py

from __future__ import annotations

import re
from typing import Any

from app.services.market_rag import build_market_search_queries


NEGATIVE_TITLE_PATTERNS = [
    r"\bqs\b",
    r"\brankings?\b",
    r"\btopuniversities\b",
    r"\btimes higher education\b",
    r"\badmission\b",
    r"\buniversity of the people\b",
    r"\bonline, affordable\b",
    r"\bsubject rankings?\b",
    r"\bapply now\b",
    r"\benroll\b",
    r"\btuition\b",
    r"\bbachelor'?s\b",
    r"\bmaster'?s\b",
    r"\bphd\b",
]

NEGATIVE_URL_PATTERNS = [
    r"topuniversities\.com",
    r"timeshighereducation\.com",
    r"uopeople\.edu",
    r"/admission",
    r"/rankings",
    r"/subject-rankings",
]

POSITIVE_SIGNAL_PATTERNS = [
    r"\bjobs?\b",
    r"\bcareers?\b",
    r"\bhiring\b",
    r"\bdemand\b",
    r"\bskills?\b",
    r"\bentry[- ]level\b",
    r"\bjunior\b",
    r"\bemployment\b",
    r"\blabor market\b",
    r"\blabour market\b",
    r"\bjob market\b",
    r"\brole[s]?\b",
    r"\bvacanc(?:y|ies)\b",
    r"\btechnician\b",
    r"\bdeveloper\b",
    r"\banalyst\b",
    r"\bqa\b",
    r"\bsupport\b",
    r"\boperations?\b",
    r"\bcoordinator\b",
]

ISRAEL_SIGNAL_PATTERNS = [
    r"\bisrael\b",
    r"\bisraeli\b",
    r"\btel aviv\b",
    r"\bjerusalem\b",
    r"\bhaifa\b",
]


def _unique_keep_order(items: list[Any]) -> list[Any]:
    seen = set()
    result = []

    for item in items:
        if isinstance(item, dict):
            key = (
                item.get("query", ""),
                item.get("searched_query", ""),
                item.get("title", ""),
                item.get("href", ""),
                item.get("body", ""),
            )
        else:
            key = item

        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _simplify_query(query: str) -> str:
    query = _clean_text(query)

    query = re.sub(r"\b20\d{2}\b", " ", query)
    query = re.sub(r"\bentry level\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\bcareer transition\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"\bwithout degree OR certificate OR course OR bootcamp\b", " jobs", query, flags=re.IGNORECASE)
    query = re.sub(r"\bdegree requirements OR certificate OR course\b", " jobs", query, flags=re.IGNORECASE)

    return _clean_text(query)


def ddgs_text_search(
    query: str,
    *,
    max_results: int = 5,
) -> list[dict[str, str]]:
    """
    Search the web using ddgs and return normalized text results.

    Requires:
        pip install ddgs
    """
    try:
        from ddgs import DDGS
    except ImportError as e:
        raise ImportError(
            "ddgs is not installed. Install it with: pip install ddgs"
        ) from e

    query = _clean_text(query)
    if not query:
        return []

    results: list[dict[str, str]] = []

    with DDGS() as ddgs:
        raw_results = ddgs.text(query, max_results=max_results)

        for item in raw_results or []:
            title = _clean_text(item.get("title", ""))
            href = _clean_text(item.get("href", ""))
            body = _clean_text(item.get("body", ""))

            if not (title or body or href):
                continue

            results.append(
                {
                    "title": title,
                    "href": href,
                    "body": body,
                }
            )

    return results


def _count_pattern_hits(text: str, patterns: list[str]) -> int:
    if not text:
        return 0

    text = text.lower()
    hits = 0
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits += 1
    return hits


def _is_low_quality_market_result(item: dict[str, str]) -> bool:
    title = _clean_text(item.get("title", ""))
    body = _clean_text(item.get("body", ""))
    href = _clean_text(item.get("href", ""))

    joined = f"{title} {body}".strip()

    negative_hits = (
        _count_pattern_hits(title, NEGATIVE_TITLE_PATTERNS)
        + _count_pattern_hits(href, NEGATIVE_URL_PATTERNS)
    )

    positive_hits = _count_pattern_hits(joined, POSITIVE_SIGNAL_PATTERNS)
    israel_hits = _count_pattern_hits(joined + " " + href, ISRAEL_SIGNAL_PATTERNS)

    # Hard reject obvious education-ranking / ad junk
    if negative_hits >= 1 and positive_hits <= 1:
        return True

    # Reject results with almost no labor/career signal
    if positive_hits == 0:
        return True

    # Very weak generic pages are not useful unless they also mention Israel
    if positive_hits == 1 and israel_hits == 0:
        return True

    return False


def _filter_market_results(results: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    filtered: list[dict[str, str]] = []
    diagnostics: list[str] = []

    for item in results:
        if not isinstance(item, dict):
            continue

        if _is_low_quality_market_result(item):
            diagnostics.append(
                f"Filtered low-quality result: {item.get('title', '')} | {item.get('href', '')}"
            )
            continue

        filtered.append(item)

    return filtered, diagnostics


def _retrieve_market_search_results_with_diagnostics(
    *,
    queries: list[str],
    search_fn=ddgs_text_search,
    max_results_per_query: int = 5,
) -> tuple[list[dict[str, str]], list[str]]:
    if not isinstance(queries, list):
        raise ValueError("queries must be a list")

    flattened: list[dict[str, str]] = []
    diagnostics: list[str] = []

    for original_query in queries:
        if not isinstance(original_query, str):
            continue

        original_query = _clean_text(original_query)
        if not original_query:
            continue

        query_variants = [original_query]
        simplified = _simplify_query(original_query)
        if simplified and simplified != original_query:
            query_variants.append(simplified)

        got_hits = False
        last_error = None

        for searched_query in _unique_keep_order(query_variants):
            try:
                hits = search_fn(searched_query, max_results=max_results_per_query)
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                diagnostics.append(
                    f"Search failed for query '{searched_query}': {last_error}"
                )
                hits = []

            if not hits:
                continue

            got_hits = True

            for hit in hits:
                if not isinstance(hit, dict):
                    continue

                flattened.append(
                    {
                        "query": original_query,
                        "searched_query": searched_query,
                        "title": _clean_text(hit.get("title", "")),
                        "href": _clean_text(hit.get("href", "")),
                        "body": _clean_text(hit.get("body", "")),
                    }
                )
            break

        if not got_hits and last_error is None:
            diagnostics.append(f"No results found for query '{original_query}'")

    flattened = _unique_keep_order(flattened)

    filtered, filter_diagnostics = _filter_market_results(flattened)
    diagnostics.extend(filter_diagnostics)

    return filtered, diagnostics


def retrieve_market_search_results(
    *,
    queries: list[str],
    search_fn=ddgs_text_search,
    max_results_per_query: int = 5,
) -> list[dict[str, str]]:
    results, _ = _retrieve_market_search_results_with_diagnostics(
        queries=queries,
        search_fn=search_fn,
        max_results_per_query=max_results_per_query,
    )
    return results


def build_market_context_from_results(
    results: list[dict[str, str]],
    *,
    max_items: int = 12,
    max_chars: int = 5000,
) -> str:
    if not isinstance(results, list):
        raise ValueError("results must be a list")

    lines: list[str] = []
    total_chars = 0

    for item in results[:max_items]:
        if not isinstance(item, dict):
            continue

        query = _clean_text(item.get("query", ""))
        searched_query = _clean_text(item.get("searched_query", ""))
        title = _clean_text(item.get("title", ""))
        body = _clean_text(item.get("body", ""))
        href = _clean_text(item.get("href", ""))

        parts = []
        if query:
            parts.append(f"Original query: {query}")
        if searched_query and searched_query != query:
            parts.append(f"Searched query: {searched_query}")
        if title:
            parts.append(f"Title: {title}")
        if body:
            parts.append(f"Snippet: {body}")
        if href:
            parts.append(f"Source: {href}")

        block = "\n".join(parts).strip()
        if not block:
            continue

        projected = total_chars + len(block) + 2
        if projected > max_chars:
            break

        lines.append(block)
        total_chars = projected

    return "\n\n".join(lines).strip()


def _build_no_results_market_context(
    *,
    country: str,
    queries: list[str],
    diagnostics: list[str],
) -> str:
    lines = [
        "No external market search results were retrieved by the retrieval layer.",
        f"Country: {country}",
        "",
        "Original queries:",
    ]

    for q in queries:
        lines.append(f"- {q}")

    if diagnostics:
        lines.append("")
        lines.append("Search diagnostics:")
        for msg in diagnostics[:20]:
            lines.append(f"- {msg}")

    lines.append("")
    lines.append(
        "This means market evidence is currently unavailable. Downstream reasoning should stay cautious and keep confidence low."
    )

    return "\n".join(lines).strip()


def retrieve_market_context(
    *,
    country: str,
    past_analysis: dict[str, Any],
    preferences_analysis: dict[str, Any],
    search_fn=ddgs_text_search,
    max_queries: int = 8,
    max_results_per_query: int = 5,
    max_context_items: int = 12,
    max_context_chars: int = 5000,
) -> dict[str, Any]:
    queries = build_market_search_queries(
        country=country,
        past_analysis=past_analysis,
        preferences_analysis=preferences_analysis,
        max_queries=max_queries,
    )

    results, diagnostics = _retrieve_market_search_results_with_diagnostics(
        queries=queries,
        search_fn=search_fn,
        max_results_per_query=max_results_per_query,
    )

    market_context = build_market_context_from_results(
        results,
        max_items=max_context_items,
        max_chars=max_context_chars,
    )

    if not market_context:
        market_context = _build_no_results_market_context(
            country=country,
            queries=queries,
            diagnostics=diagnostics,
        )

    return {
        "country": country,
        "queries": queries,
        "results": results,
        "results_count": len(results),
        "search_errors": diagnostics,
        "market_context": market_context,
    }