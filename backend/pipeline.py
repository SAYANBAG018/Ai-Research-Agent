
"""
Research pipeline orchestration.

Connects the search agent, source validation, webpage scraper,
writer, critic, and report exporters.

Designed to keep AI requests within smaller token budgets.
"""

import re
import time

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

from groq import RateLimitError

from agents import build_search_agent, writer_chain, critic_chain
from tools import scrape_url
from research_quality import validate_sources
from report_export import save_markdown, save_pdf


# ============================================================
# CONFIGURATION
# ============================================================

MAX_URLS = 3
MAX_WORKERS = 3

# Keep AI input substantially smaller.
MAX_SEARCH_CHARS = 2500
MAX_SCRAPED_CHARS = 7000

MAX_WRITER_SEARCH_CHARS = 2200
MAX_WRITER_SCRAPED_CHARS = 6000

MAX_CRITIC_REPORT_CHARS = 5000
MAX_CRITIC_RESEARCH_CHARS = 5500

MAX_VALIDATION_CHARS = 1000
MAX_STATUS_CHARS = 1200

RETRY_COUNT = 2
RETRY_BASE_SECONDS = 30

USABLE_EXTRACTION_STATUSES = {"SUCCESS", "PARTIAL"}


# ============================================================
# GENERAL HELPERS
# ============================================================

def as_text(value: Any) -> str:
    """Convert LangChain response objects into plain text."""

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    content = getattr(value, "content", None)

    if content is not None:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts = []

            for block in content:
                if isinstance(block, dict):
                    text_value = block.get("text")

                    if text_value:
                        parts.append(str(text_value))

                elif block is not None:
                    parts.append(str(block))

            return "\n".join(parts)

    return str(value)


def truncate_text(text: Any, limit: int) -> str:
    """Safely truncate text to a maximum character count."""

    value = as_text(text)

    if len(value) <= limit:
        return value

    return value[:limit] + "\n[Content truncated to control AI input size.]"


def invoke_with_retry(runnable, inputs, retries=RETRY_COUNT):
    """
    Invoke a LangChain runnable.

    Retry temporary rate-limit failures, but do not repeatedly retry
    requests rejected because their individual input is too large.
    """

    for attempt in range(retries + 1):

        try:
            return runnable.invoke(inputs)

        except RateLimitError as exc:

            error_text = str(exc).lower()

            # A request-size error will not be fixed by waiting.
            if (
                "requested" in error_text
                and (
                    "reduce your message size" in error_text
                    or "tokens per minute" in error_text
                )
            ):
                raise RuntimeError(
                    "Groq rejected an AI request because its token "
                    "requirement exceeded the available limit. "
                    "Reduce the research input size or use a model "
                    "with a higher token allowance."
                ) from exc

            if attempt >= retries:
                raise

            wait_time = RETRY_BASE_SECONDS * (attempt + 1)

            print(
                f"\n[GROQ] Temporary rate limit reached. "
                f"Waiting {wait_time} seconds before retry "
                f"({attempt + 1}/{retries})..."
            )

            time.sleep(wait_time)

        except Exception as exc:

            error_text = str(exc).lower()
            status_code = getattr(exc, "status_code", None)

            if status_code == 413 or (
                "requested" in error_text
                and "tokens per minute" in error_text
            ):
                raise RuntimeError(
                    "Groq rejected the request because it exceeded "
                    "the available token limit. The pipeline has "
                    "stopped this request instead of retrying the "
                    "same oversized input."
                ) from exc

            raise


# ============================================================
# URL EXTRACTION AND VALIDATION
# ============================================================

URL_PATTERN = re.compile(
    r'https?://[^\s<>"\]\[{}]+',
    re.IGNORECASE,
)


def is_valid_http_url(url: str) -> bool:
    """Check whether a URL is a valid HTTP or HTTPS URL."""

    if not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())

        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )

    except (TypeError, ValueError):
        return False


def extract_urls(text: str) -> list[str]:
    """Extract unique HTTP(S) URLs from text."""

    if not text:
        return []

    found = URL_PATTERN.findall(text)
    cleaned_urls = []

    for raw_url in found:

        url = raw_url.rstrip(".,;:!?")

        if is_valid_http_url(url) and url not in cleaned_urls:
            cleaned_urls.append(url)

    return cleaned_urls


# ============================================================
# SCRAPE RESULT PARSING
# ============================================================

def parse_scrape_metadata(result_text: str) -> dict:
    """Extract structured metadata from scraper output."""

    metadata = {}

    keys = {
        "EXTRACTION_STATUS": "status",
        "EXTRACTION_METHOD": "method",
        "SOURCE_URL": "url",
        "PAGE_TITLE": "title",
        "PUBLICATION_DATE": "publication_date",
        "QUALITY_SCORE": "quality_score",
        "WORD_COUNT": "word_count",
        "PARAGRAPH_COUNT": "paragraph_count",
        "QUALITY_REASON": "quality_reason",
    }

    for line in result_text.splitlines():

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        normalized_key = key.strip()

        if normalized_key in keys:
            metadata[keys[normalized_key]] = value.strip()

    return metadata


def scrape_single_url(url: str) -> dict:
    """Scrape one URL and preserve extraction metadata."""

    print(f"\n[SCRAPER] Starting: {url}")

    try:

        result = scrape_url.invoke({"url": url})
        result_text = as_text(result)

        metadata = parse_scrape_metadata(result_text)

        status = metadata.get("status", "FAILED").upper()

        usable = status in USABLE_EXTRACTION_STATUSES

        if usable:

            print(
                f"[SCRAPER] {status}: {url} "
                f"({len(result_text)} characters)"
            )

        else:

            print(f"[SCRAPER] No usable extraction: {url}")

        return {
            "url": url,
            "content": result_text if usable else "",
            "success": status == "SUCCESS",
            "usable": usable,
            "status": status,
            "metadata": metadata,
            "error": None,
        }

    except Exception as exc:

        error_message = str(exc)

        print(f"[SCRAPER ERROR] {url}: {error_message}")

        return {
            "url": url,
            "content": "",
            "success": False,
            "usable": False,
            "status": "FAILED",
            "metadata": {},
            "error": error_message,
        }


def parallel_scrape(
    urls: list[str],
    max_workers: int = MAX_WORKERS,
) -> list[dict]:
    """Scrape URLs concurrently and preserve their original order."""

    urls = list(
        dict.fromkeys(
            url for url in urls
            if is_valid_http_url(url)
        )
    )

    if not urls:
        return []

    worker_count = max(1, min(max_workers, len(urls)))

    print(
        f"\n[SCRAPER] Processing {len(urls)} URLs "
        f"with {worker_count} workers..."
    )

    results_by_url = {}

    with ThreadPoolExecutor(max_workers=worker_count) as executor:

        future_to_url = {
            executor.submit(scrape_single_url, url): url
            for url in urls
        }

        for future in as_completed(future_to_url):

            url = future_to_url[future]

            try:
                results_by_url[url] = future.result()

            except Exception as exc:

                results_by_url[url] = {
                    "url": url,
                    "content": "",
                    "success": False,
                    "usable": False,
                    "status": "FAILED",
                    "metadata": {},
                    "error": str(exc),
                }

    ordered_results = [
        results_by_url[url]
        for url in urls
        if url in results_by_url
    ]

    usable_count = sum(
        item["usable"] for item in ordered_results
    )

    success_count = sum(
        item["success"] for item in ordered_results
    )

    print(
        f"\n[SCRAPER] Fully successful: "
        f"{success_count}/{len(urls)} | "
        f"Usable including partial: "
        f"{usable_count}/{len(urls)}"
    )

    return ordered_results


# ============================================================
# SOURCE VALIDATION HELPERS
# ============================================================

def validate_and_filter_urls(
    urls: list[str],
) -> tuple[list[str], list[dict]]:
    """
    Validate URLs and retain source screening metadata.
    """

    valid_urls = [
        url for url in urls
        if is_valid_http_url(url)
    ]

    invalid_urls = [
        url for url in urls
        if not is_valid_http_url(url)
    ]

    validation_results = (
        validate_sources(valid_urls)
        if valid_urls
        else []
    )

    validation_results = list(validation_results or [])

    for url in invalid_urls:

        validation_results.append({
            "domain": url,
            "category": "INVALID_URL",
            "score": 0,
            "source_type": "INVALID",
            "warnings": [
                "URL did not pass HTTP/HTTPS validation"
            ],
            "validation_method": "URL syntax check",
            "note": "Not sent to the scraper",
        })

    return valid_urls, validation_results


# ============================================================
# COMPACT RESEARCH CONTEXT
# ============================================================

def build_scraped_context(scraped_results: list[dict]) -> str:
    """
    Build a compact research context from extracted sources.

    Each source gets a fair share of the total character budget.
    """

    usable_results = [
        item for item in scraped_results
        if item.get("usable")
    ]

    if not usable_results:
        return ""

    per_source_limit = max(
        1000,
        MAX_WRITER_SCRAPED_CHARS // len(usable_results),
    )

    sections = []
    remaining = MAX_WRITER_SCRAPED_CHARS

    for index, item in enumerate(usable_results, start=1):

        if remaining <= 0:
            break

        metadata = item.get("metadata", {})

        header = (
            f"\n\nSOURCE {index}\n"
            f"URL: {item.get('url', '')}\n"
            f"TITLE: {metadata.get('title', 'Not available')}\n"
            f"PUBLICATION DATE: "
            f"{metadata.get('publication_date', 'Not available')}\n"
            f"EXTRACTION STATUS: {item.get('status', 'UNKNOWN')}\n"
            f"CONTENT:\n"
        )

        available_content = max(
            0,
            remaining - len(header),
        )

        content_limit = min(
            per_source_limit,
            available_content,
        )

        if content_limit <= 0:
            break

        content = truncate_text(
            item.get("content", ""),
            content_limit,
        )

        section = header + content

        sections.append(section)

        remaining -= len(section)

    return "\n".join(sections)


def build_scraping_status(scraped_results: list[dict]) -> str:
    """Create a short status summary without large error messages."""

    lines = []

    for item in scraped_results:

        metadata = item.get("metadata", {})

        lines.append(
            f"- URL: {item.get('url')}\n"
            f"  Status: {item.get('status')}\n"
            f"  Title: {metadata.get('title', 'Not available')}\n"
            f"  Error: {truncate_text(item.get('error') or 'None', 150)}"
        )

    return truncate_text(
        "\n".join(lines),
        MAX_STATUS_CHARS,
    )


# ============================================================
# MAIN RESEARCH PIPELINE
# ============================================================

def run_research_pipeline(topic: str) -> dict:
    """Run search, validation, scraping, writing, critique and export."""

    topic = (topic or "").strip()

    if not topic:
        raise ValueError("Please provide a research topic.")

    state = {
        "topic": topic,
    }

    # --------------------------------------------------------
    # STEP 1: SEARCH AGENT
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 1 - SEARCH AGENT")
    print("=" * 55)

    search_agent = build_search_agent()

    search_prompt = f"""
Research this topic:

{topic}

Perform no more than TWO focused searches.

Prioritize:
- Academic research
- Government and international organizations
- Universities
- Reputable news organizations
- Credible industry reports

Find:
- Important findings
- Useful statistics
- Publication dates
- Original source URLs

Prefer primary sources.

Do not invent facts, statistics or sources.
Keep the final result concise.
"""

    search_result = invoke_with_retry(
        search_agent,
        {
            "messages": [
                ("user", search_prompt)
            ]
        },
    )

    if isinstance(search_result, dict):

        messages = search_result.get("messages", [])

        if messages:
            state["search_results"] = as_text(messages[-1])
        else:
            state["search_results"] = as_text(search_result)

    else:

        state["search_results"] = as_text(search_result)

    if not state["search_results"].strip():

        raise ValueError(
            "The search agent returned an empty response."
        )

    print("\n[SEARCH] Completed.")

    print(
        "[SEARCH] Result length:",
        len(state["search_results"]),
        "characters",
    )

    # --------------------------------------------------------
    # STEP 2: URL EXTRACTION
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 2 - URL EXTRACTION")
    print("=" * 55)

    discovered_urls = extract_urls(
        state["search_results"]
    )

    state["discovered_urls"] = discovered_urls

    if not discovered_urls:

        raise ValueError(
            "No valid HTTP/HTTPS URLs were found in search results."
        )

    urls_to_check = discovered_urls[:MAX_URLS]

    print(f"\nURLs discovered: {len(discovered_urls)}")
    print(f"URLs selected: {len(urls_to_check)}")

    for url in urls_to_check:
        print(url)

    # --------------------------------------------------------
    # STEP 3: SOURCE VALIDATION
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 3 - SOURCE VALIDATION")
    print("=" * 55)

    urls_to_scrape, state["sources"] = (
        validate_and_filter_urls(urls_to_check)
    )

    for source in state["sources"]:

        if not isinstance(source, dict):
            print(source)
            continue

        print(
            f"{source.get('domain', 'Unknown')} | "
            f"{source.get('category', 'Unknown')} | "
            f"Score: {source.get('score', 'N/A')}/10"
        )

    if not urls_to_scrape:

        raise ValueError(
            "No valid URLs remained after URL validation."
        )

    # --------------------------------------------------------
    # STEP 4: PARALLEL SCRAPING
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 4 - PARALLEL WEB SCRAPING")
    print("=" * 55)

    state["scraped_results"] = parallel_scrape(
        urls_to_scrape
    )

    state["successful_scrapes"] = [
        item for item in state["scraped_results"]
        if item["success"]
    ]

    state["usable_scrapes"] = [
        item for item in state["scraped_results"]
        if item["usable"]
    ]

    state["failed_scrapes"] = [
        item for item in state["scraped_results"]
        if not item["usable"]
    ]

    if not state["usable_scrapes"]:

        failure_details = "\n".join(
            f"- {item['url']}: "
            f"{item.get('error') or item['status']}"
            for item in state["failed_scrapes"]
        )

        raise ValueError(
            "No usable article content could be extracted.\n"
            f"{failure_details}"
        )

    # Preserve original complete extraction results in state.
    state["scraped_content"] = "\n\n".join(
        item["content"]
        for item in state["usable_scrapes"]
    )

    print(
        "\nTotal extracted characters:",
        len(state["scraped_content"]),
    )

    # --------------------------------------------------------
    # STEP 5: BUILD COMPACT RESEARCH CONTEXT
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("PREPARING COMPACT RESEARCH CONTEXT")
    print("=" * 55)

    compact_search = truncate_text(
        state["search_results"],
        MAX_WRITER_SEARCH_CHARS,
    )

    compact_scraped = build_scraped_context(
        state["scraped_results"]
    )

    compact_sources = []

    for source in state["sources"]:

        if isinstance(source, dict):

            compact_sources.append({
                "domain": source.get("domain"),
                "category": source.get("category"),
                "score": source.get("score"),
                "source_type": source.get("source_type"),
            })

    source_validation_text = truncate_text(
        str(compact_sources),
        MAX_VALIDATION_CHARS,
    )

    scraping_status = build_scraping_status(
        state["scraped_results"]
    )

    successful_urls = [
        item["url"]
        for item in state["usable_scrapes"]
    ]

    research_combined = f"""
RESEARCH TOPIC:
{topic}

SEARCH FINDINGS:
{compact_search}

EXTRACTED SOURCE CONTENT:
{compact_scraped}

SUCCESSFULLY EXTRACTED SOURCE URLS:
{chr(10).join(successful_urls)}

SOURCE SCREENING:
{source_validation_text}

EXTRACTION STATUS:
{scraping_status}

IMPORTANT INSTRUCTIONS:

1. Use only the supplied research evidence.
2. Do not invent facts, statistics or quotations.
3. Cite the supplied source URLs where relevant.
4. Distinguish search-result claims from extracted evidence.
5. Mention conflicting evidence and research limitations.
6. Do not treat domain scores as proof of factual accuracy.
7. Clearly identify claims that require further verification.
"""

    state["research"] = research_combined

    print(
        "[RESEARCH] Compact context:",
        len(research_combined),
        "characters",
    )

    # --------------------------------------------------------
    # STEP 6: WRITER AGENT
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 6 - WRITER AGENT")
    print("=" * 55)

    writer_result = invoke_with_retry(
        writer_chain,
        {
            "topic": topic,
            "research": research_combined,
        },
    )

    state["report"] = as_text(writer_result)

    if not state["report"].strip():

        raise ValueError(
            "The writer agent returned an empty report."
        )

    print("\n[WRITER] Report generated successfully.")

    print("\nFINAL RESEARCH REPORT:\n")
    print(state["report"])

    # --------------------------------------------------------
    # STEP 7: CRITIC AGENT
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 7 - CRITIC AGENT")
    print("=" * 55)

    critic_report = truncate_text(
        state["report"],
        MAX_CRITIC_REPORT_CHARS,
    )

    critic_research = truncate_text(
        research_combined,
        MAX_CRITIC_RESEARCH_CHARS,
    )

    critic_result = invoke_with_retry(
        critic_chain,
        {
            "report": critic_report,
            "research": critic_research,
        },
    )

    state["feedback"] = as_text(critic_result)

    print("\n[CRITIC] Evaluation completed.")

    print("\nCRITIC FEEDBACK:\n")
    print(state["feedback"])

    # --------------------------------------------------------
    # STEP 8: REPORT EXPORT
    # --------------------------------------------------------

    print("\n" + "=" * 55)
    print("STEP 8 - REPORT EXPORT")
    print("=" * 55)

    markdown_path = save_markdown(
        topic,
        state["report"],
        state["feedback"],
    )

    pdf_path = save_pdf(
        topic,
        state["report"],
        state["feedback"],
    )

    state["markdown_file"] = str(markdown_path)
    state["pdf_file"] = str(pdf_path)

    print("\nMarkdown:", state["markdown_file"])
    print("PDF:", state["pdf_file"])

    print("\n" + "=" * 55)
    print("RESEARCH PIPELINE COMPLETED")
    print("=" * 55)

    return state


# ============================================================
# COMMAND-LINE EXECUTION
# ============================================================

if __name__ == "__main__":

    research_topic = input(
        "\nEnter a research topic: "
    ).strip()

    try:

        result = run_research_pipeline(
            research_topic
        )

        print("\nPipeline completed successfully.")

        print(
            "Markdown report:",
            result.get("markdown_file"),
        )

        print(
            "PDF report:",
            result.get("pdf_file"),
        )

    except Exception as exc:

        print("\nPIPELINE FAILED:", str(exc))


#uvicorn main:app --reload --port 8000