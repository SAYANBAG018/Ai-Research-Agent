import os
import re
import json
import html
import requests
try:
    import trafilatura
except ImportError:
    trafilatura = None


from difflib import SequenceMatcher

from bs4 import BeautifulSoup

from tavily import TavilyClient

from langchain.tools import tool

from dotenv import load_dotenv

from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


# ============================================================

# 1. CONFIGURATION

# ============================================================


load_dotenv()


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


tavily = (

    TavilyClient(api_key=TAVILY_API_KEY)

    if TAVILY_API_KEY

    else None

)


USER_AGENT = (

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

    "AppleWebKit/537.36 (KHTML, like Gecko) "

    "Chrome/131.0.0.0 Safari/537.36"

)


REQUEST_TIMEOUT = (10, 25)


MIN_CONTENT_LENGTH = 300

MAX_CONTENT_LENGTH = 8000


# Domains to prioritize when search relevance is comparable.

# This is a ranking preference, NOT a factual accuracy guarantee.


PREFERRED_DOMAINS = [

    "openai.com",

    "deepmind.google",

    "ai.google",

    "anthropic.com",

    "nvidia.com",

    "microsoft.com",

    "arxiv.org",

    "nature.com",

    "science.org",

    "huggingface.co",

    "hai.stanford.edu",

]


def get_source_domain(url: str) -> str:
    """Return a normalized hostname for a URL."""
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except (TypeError, ValueError):
        return ""


def preferred_domain_priority(url: str) -> int:
    """Lower values indicate a preferred domain; this is not an accuracy score."""
    domain = get_source_domain(url)
    for index, preferred in enumerate(PREFERRED_DOMAINS):
        if domain == preferred or domain.endswith("." + preferred):
            return index
    return len(PREFERRED_DOMAINS)


def rank_search_results(results: list) -> list:
    """
    Rank by Tavily relevance first, then preferred-domain order.
    Preferred domains are a discovery preference, not proof of accuracy.
    """
    indexed = []
    for index, result in enumerate(results or []):
        if not isinstance(result, dict):
            continue
        try:
            relevance = float(result.get("score") or 0.0)
        except (TypeError, ValueError):
            relevance = 0.0
        indexed.append(
            (index, relevance, preferred_domain_priority(result.get("url", "")), result)
        )
    indexed.sort(key=lambda item: (-item[1], item[2], item[0]))
    return [item[3] for item in indexed]



# ============================================================

# 2. URL VALIDATION

# ============================================================


def validate_url(url: str) -> bool:

    """Validate that a URL uses HTTP or HTTPS."""


    if not isinstance(url, str):

        return False


    try:

        parsed = urlparse(url.strip())


        return (

            parsed.scheme in ("http", "https")

            and bool(parsed.hostname)

            and not parsed.username

            and not parsed.password

        )


    except Exception:

        return False


# ============================================================

# 3. TEXT NORMALIZATION

# ============================================================


def normalize_text(text: str) -> str:

    """Normalize text for comparison."""


    text = html.unescape(text or "")

    text = text.lower()


    text = re.sub(

        r"[^\w\s]",

        " ",

        text

    )


    text = re.sub(

        r"\s+",

        " ",

        text

    )


    return text.strip()


def title_matches(line: str, title: str) -> bool:

    """

    Compare an extracted heading with a page title.


    Handles differences such as:

        Article title

        Article title - IEA

        Article title | Website

    """


    if not line or not title:

        return False


    normalized_line = normalize_text(line)

    normalized_title = normalize_text(title)


    if not normalized_line or not normalized_title:

        return False


    if normalized_line == normalized_title:

        return True


    # Remove common website-name suffixes.

    title_core = re.split(

        r"\s[-|–—]\s",

        title,

        maxsplit=1

    )[0]


    normalized_core = normalize_text(title_core)


    if (

        normalized_core

        and (

            normalized_core in normalized_line

            or normalized_line in normalized_core

        )

        and min(len(normalized_core), len(normalized_line)) > 25

    ):

        return True


    # Compare matching word coverage.

    title_words = set(normalized_core.split())

    line_words = set(normalized_line.split())


    if title_words:

        overlap = len(title_words & line_words) / len(title_words)


        if overlap >= 0.85:

            return True


    # Last-resort similarity comparison.

    similarity = SequenceMatcher(

        None,

        normalized_core,

        normalized_line

    ).ratio()


    return similarity >= 0.85


# ============================================================

# 4. DATE EXTRACTION

# ============================================================


def find_date_in_text(text: str) -> str:

    """Find a recognizable date in a short text section."""


    if not text:

        return "Not found"


    patterns = [

        r"\b\d{4}-\d{2}-\d{2}\b",


        r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b",


        r"\b[A-Za-z]+\s+\d{1,2},?\s+\d{4}\b",

    ]


    for pattern in patterns:

        match = re.search(

            pattern,

            text,

            re.IGNORECASE

        )


        if match:

            return match.group(0).strip()


    return "Not found"


def extract_publication_date(content: str) -> str:

    """

    General date extraction.


    Use extract_article_publication_date() when an article title

    is available because general date extraction can select an

    unrelated date elsewhere on the page.

    """


    if not content:

        return "Not found"


    patterns = [

        (

            r"(?:Published|Publication date|Published on|"

            r"Date published|Date):?\s*"

            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})"

        ),

        (

            r"(?:Published|Publication date|Published on|"

            r"Date published|Date):?\s*"

            r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})"

        ),

    ]


    for pattern in patterns:

        match = re.search(

            pattern,

            content,

            re.IGNORECASE

        )


        if match:

            return match.group(1).strip()


    return find_date_in_text(content)


def extract_date_from_soup(soup: BeautifulSoup) -> str:

    """Extract a date from common HTML metadata fields."""


    selectors = [

        ("meta", {"property": "article:published_time"}),

        ("meta", {"name": "date"}),

        ("meta", {"name": "publishdate"}),

        ("meta", {"name": "publication_date"}),

        ("meta", {"name": "DC.date"}),

        ("meta", {"itemprop": "datePublished"}),

    ]


    for tag_name, attributes in selectors:


        tag = soup.find(

            tag_name,

            attrs=attributes

        )


        if tag:


            date_value = (

                tag.get("content")

                or tag.get("datetime")

            )


            if date_value:

                return date_value.strip()


    # Check JSON-LD metadata.

    for script in soup.find_all(

        "script",

        type="application/ld+json"

    ):


        try:

            data = json.loads(

                script.string or script.get_text()

            )


            objects = (

                data if isinstance(data, list)

                else [data]

            )


            for item in objects:


                if not isinstance(item, dict):

                    continue


                date_value = (

                    item.get("datePublished")

                    or item.get("dateCreated")

                )


                if date_value:

                    return str(date_value)


        except (json.JSONDecodeError, TypeError):

            continue


    return "Not found"


def extract_article_publication_date(

    content: str,

    title: str

) -> str:

    """

    Look for a date immediately after the article heading.


    This avoids selecting unrelated dates from navigation,

    recommendations or other website sections.

    """


    cleaned = clean_extracted_content(content)


    lines = [

        line.strip()

        for line in cleaned.splitlines()

        if line.strip()

    ]


    for index, line in enumerate(lines):


        if title_matches(line, title):


            # The article date usually appears close to its heading.

            nearby_lines = lines[

                index + 1:index + 9

            ]


            for nearby_line in nearby_lines:


                date_value = find_date_in_text(

                    nearby_line

                )


                if date_value != "Not found":

                    return date_value


            break


    return "Not found"


# ============================================================

# 5. CONTENT CLEANING

# ============================================================


def clean_extracted_content(content: str) -> str:

    """

    Remove common Markdown, image and formatting noise.

    """


    if not isinstance(content, str):

        return ""


    content = html.unescape(content)


    # Remove Markdown images.

    content = re.sub(

        r"!\[[^\]]*\]\([^)]*\)",

        "",

        content

    )


    # Remove HTML tags.

    content = re.sub(

        r"<[^>]+>",

        " ",

        content

    )


    # Keep link text and remove link destinations.

    content = re.sub(

        r"\[([^\]]+)\]\([^)]*\)",

        r"\1",

        content

    )


    # Remove Markdown headings.

    content = re.sub(

        r"(?m)^\s{0,3}#{1,6}\s*",

        "",

        content

    )


    # Remove Markdown formatting characters.

    content = re.sub(

        r"[\*\_\`\~]{1,3}",

        "",

        content

    )


    navigation_lines = {

        "sign in",

        "create an account",

        "subscribe",

        "member countries",

        "data explorers",

        "view all",

        "latest news",

        "trending topics",

        "contact us",

        "privacy policy",

        "terms and conditions",

        "home",

        "menu",

        "search",

        "share",

        "print",

    }


    cleaned_lines = []


    for line in content.splitlines():


        line = re.sub(

            r"\s+",

            " ",

            line

        ).strip()


        if not line:

            continue


        if line.lower().strip(" .:-") in navigation_lines:

            continue


        if len(line) < 3:

            continue


        cleaned_lines.append(line)


    return "\n\n".join(cleaned_lines)


# ============================================================

# 6. ARTICLE BODY EXTRACTION

# ============================================================


def extract_article_body(

    content: str,

    title: str = ""

) -> str:

    """

    Isolate article text between its heading and related-content

    or footer markers.

    """


    cleaned = clean_extracted_content(content)


    lines = [

        line.strip()

        for line in cleaned.splitlines()

        if line.strip()

    ]


    start_index = None


    # Locate the article heading.

    for index, line in enumerate(lines):


        if title_matches(line, title):

            start_index = index

            break


    if start_index is None:

        return ""


    article_lines = lines[start_index + 1:]


    end_markers = {

        "related tags",

        "related articles",

        "related content",

        "newsletters",

        "subscription successful",

        "thank you for subscribing",

        "share this article",

        "follow us",

    }


    body_lines = []


    for line in article_lines:


        normalized_line = normalize_text(line)


        if normalized_line in end_markers:

            break


        # Remove common article category labels.

        if normalized_line in {

            "news",

            "commentary",

            "analysis",

            "press release",

        }:

            continue


        # Keep the article body, but not its date line.

        if find_date_in_text(line) == line:

            continue


        body_lines.append(line)


    return "\n\n".join(body_lines).strip()


# ============================================================

# 7. ARTICLE QUALITY ASSESSMENT

# ============================================================


def assess_article_quality(

    content: str,

    title: str = ""

) -> dict:

    """

    Evaluate the isolated article body.


    SUCCESS means basic article-structure checks passed.

    It does NOT mean factual accuracy was verified.

    """


    article_body = extract_article_body(

        content,

        title

    )


    if not article_body:


        return {

            "status": "PARTIAL",

            "score": 0,

            "word_count": 0,

            "paragraph_count": 0,

            "substantial_paragraphs": 0,

            "reason": "Article heading could not be located",

            "cleaned_content": "",

            "publication_date": "Not found",

        }


    words = re.findall(

        r"\b[\w'-]+\b",

        article_body

    )


    word_count = len(words)


    paragraphs = [

        paragraph.strip()

        for paragraph in article_body.split("\n\n")

        if paragraph.strip()

    ]


    substantial_paragraphs = [

        paragraph

        for paragraph in paragraphs

        if len(paragraph) >= 120

    ]


    score = 0


    if word_count >= 250:

        score += 1


    if word_count >= 500:

        score += 1


    if len(substantial_paragraphs) >= 3:

        score += 1


    if len(paragraphs) >= 5:

        score += 1


    if title:

        score += 1


    if (

        word_count >= 250

        and len(substantial_paragraphs) >= 3

        and len(paragraphs) >= 5

    ):


        status = "SUCCESS"

        reason = "Main article body successfully isolated"


    else:


        status = "PARTIAL"

        reason = "Article body is incomplete or too short"


    publication_date = extract_article_publication_date(

        content,

        title

    )


    return {

        "status": status,

        "score": score,

        "word_count": word_count,

        "paragraph_count": len(paragraphs),

        "substantial_paragraphs": len(substantial_paragraphs),

        "reason": reason,

        "cleaned_content": article_body,

        "publication_date": publication_date,

    }


# ============================================================

# 8. RESULT FORMATTING

# ============================================================


def format_result(

    url: str,

    method: str,

    title: str,

    publication_date: str,

    quality: dict,

) -> str:


    cleaned_content = quality["cleaned_content"]


    return f"""

EXTRACTION_STATUS: {quality['status']}


EXTRACTION_METHOD: {method}


SOURCE_URL: {url}


PAGE_TITLE: {title}


PUBLICATION_DATE: {publication_date}


QUALITY_SCORE: {quality['score']}/5


WORD_COUNT: {quality['word_count']}


PARAGRAPH_COUNT: {quality['paragraph_count']}


QUALITY_REASON: {quality['reason']}


EXTRACTED_CONTENT:


{cleaned_content[:MAX_CONTENT_LENGTH]}

"""


# ============================================================

# 9. LAYER 1: BEAUTIFULSOUP

# ============================================================


def extract_with_beautifulsoup(url: str) -> dict:


    response = requests.get(

        url,

        timeout=REQUEST_TIMEOUT,

        headers={"User-Agent": USER_AGENT}

    )


    response.raise_for_status()


    content_type = response.headers.get(

        "Content-Type",

        ""

    )


    if "html" not in content_type.lower():

        raise ValueError("URL did not return HTML")


    soup = BeautifulSoup(

        response.text,

        "html.parser"

    )


    publication_date = extract_date_from_soup(

        soup

    )


    # Remove irrelevant elements.

    for tag in soup([

        "script",

        "style",

        "nav",

        "footer",

        "header",

        "aside",

        "noscript",

        "form",

        "svg",

        "iframe",

    ]):

        tag.decompose()


    # Prefer H1 over the generic browser title.

    heading = soup.find("h1")


    title = (

        heading.get_text(" ", strip=True)

        if heading

        else (

            soup.title.get_text(strip=True)

            if soup.title

            else "Unknown title"

        )

    )


    article = soup.find("article")


    if article:

        element = article

    else:

        main = soup.find("main")

        element = main or soup.body or soup


    for tag in element.find_all([

        "nav",

        "footer",

        "header",

        "aside",

        "form",

    ]):

        tag.decompose()


    content = element.get_text(

        separator="\n\n",

        strip=True

    )


    return {

        "title": title,

        "content": content,

        "publication_date": publication_date,

    }


# ============================================================

# 10. LAYER 2: TRAFILATURA

# ============================================================


def extract_with_trafilatura(url: str) -> dict:


    if trafilatura is None:
        raise RuntimeError("Trafilatura is not installed")

    downloaded = trafilatura.fetch_url(url)


    if not downloaded:

        raise ValueError(

            "Trafilatura could not download webpage"

        )


    content = trafilatura.extract(

        downloaded,

        url=url,

        output_format="markdown",

        include_tables=True,

        include_links=True,

        favor_precision=True,

    )


    if not content:

        raise ValueError(

            "Trafilatura returned empty content"

        )


    metadata = trafilatura.extract_metadata(

        downloaded

    )


    title = (

        metadata.title

        if metadata and metadata.title

        else "Unknown title"

    )


    publication_date = (

        metadata.date

        if metadata and metadata.date

        else "Not found"

    )


    return {

        "title": title,

        "content": content,

        "publication_date": publication_date,

    }


# ============================================================

# 11. LAYER 3: TAVILY ADVANCED EXTRACT

# ============================================================


def extract_with_tavily(url: str) -> dict:


    if tavily is None:

        raise ValueError(

            "TAVILY_API_KEY is missing from .env"

        )


    result = tavily.extract(

        urls=[url],

        extract_depth="advanced",

        format="markdown"

    )


    results = result.get(

        "results",

        []

    )


    if not results:

        raise ValueError(

            "Tavily returned no extraction results"

        )


    extracted = results[0]


    content = extracted.get(

        "raw_content",

        ""

    )


    if not content:

        raise ValueError(

            "Tavily returned empty content"

        )


    title = extracted.get(

        "title",

        "Unknown title"

    )


    publication_date = extracted.get(

        "published_date",

        "Not found"

    )


    return {

        "title": title,

        "content": content,

        "publication_date": publication_date,

    }


# ============================================================

# 12. LAYER 4: PLAYWRIGHT

# ============================================================


def extract_with_playwright(url: str) -> dict:


    if sync_playwright is None:
        raise RuntimeError("Playwright is not installed")

    with sync_playwright() as playwright:


        browser = playwright.chromium.launch(

            headless=True

        )


        try:


            page = browser.new_page(

                user_agent=USER_AGENT

            )


            page.goto(

                url,

                wait_until="domcontentloaded",

                timeout=30000

            )


            page.wait_for_timeout(2000)


            rendered_html = page.content()


            soup = BeautifulSoup(

                rendered_html,

                "html.parser"

            )


            heading = soup.find("h1")


            title = (

                heading.get_text(" ", strip=True)

                if heading

                else page.title()

            )


            publication_date = extract_date_from_soup(

                soup

            )


            content = trafilatura.extract(

                rendered_html,

                url=url,

                output_format="markdown",

                include_tables=True,

                include_links=True,

                favor_precision=True,

            )


            if not content:

                raise ValueError(

                    "Playwright returned empty content"

                )


            return {

                "title": title,

                "content": content,

                "publication_date": publication_date,

            }


        finally:

            browser.close()


# ============================================================

# 13. MASTER SCRAPER WITH FALLBACKS

# ============================================================


def scrape_url_fallback(url: str) -> str:

    """

    Try multiple extraction methods.


    SUCCESS:

        Article body passes basic structural checks.


    PARTIAL:

        Some content was retrieved but checks were not passed.


    FAILED:

        No usable content could be extracted.

    """


    if not validate_url(url):


        return """

EXTRACTION_STATUS: FAILED


ERROR: Invalid HTTP/HTTPS URL

"""


    extraction_methods = [

        (

            "BeautifulSoup",

            extract_with_beautifulsoup

        ),

        (

            "Trafilatura",

            extract_with_trafilatura

        ),

        (

            "Tavily Advanced Extract",

            extract_with_tavily

        ),

        (

            "Playwright + Trafilatura",

            extract_with_playwright

        ),

    ]


    print(

        f"\n[SCRAPER] Starting: {url}"

    )


    errors = []


    best_partial = None

    best_partial_score = -1


    for method_name, extractor in extraction_methods:


        try:


            print(

                f"[SCRAPER] Trying {method_name}..."

            )


            result = extractor(url)


            title = result.get(

                "title",

                "Unknown title"

            )


            content = result.get(

                "content",

                ""

            )


            metadata_date = result.get(

                "publication_date",

                "Not found"

            )


            if (

                not content

                or len(content.strip()) < MIN_CONTENT_LENGTH

            ):

                raise ValueError(

                    "Insufficient extracted content"

                )


            quality = assess_article_quality(

                content,

                title

            )


            # Article-specific visible date takes priority.

            article_date = quality["publication_date"]


            if article_date != "Not found":

                publication_date = article_date

            else:

                publication_date = metadata_date


            if not publication_date:

                publication_date = "Not found"


            print(

                f"[SCRAPER] {method_name} | "

                f"Status: {quality['status']} | "

                f"Words: {quality['word_count']} | "

                f"Quality: {quality['score']}/5"

            )


            if quality["status"] == "SUCCESS":


                print(

                    f"[SCRAPER] SUCCESS | {method_name}"

                )


                return format_result(

                    url=url,

                    method=method_name,

                    title=title,

                    publication_date=publication_date,

                    quality=quality,

                )


            # Keep the best partial result.

            if quality["score"] > best_partial_score:


                best_partial_score = quality["score"]


                best_partial = {

                    "method": method_name,

                    "title": title,

                    "publication_date": publication_date,

                    "quality": quality,

                }


            print(

                f"[SCRAPER] PARTIAL | {method_name} | "

                f"{quality['reason']}"

            )


        except Exception as e:


            error_message = str(e)


            print(

                f"[SCRAPER] {method_name} failed: "

                f"{error_message[:200]}"

            )


            errors.append(

                f"{method_name}: {error_message[:200]}"

            )


    # Return the best partial extraction if no method passes.

    if best_partial:


        print(

            "[SCRAPER] Returning best PARTIAL extraction"

        )


        return format_result(

            url=url,

            method=best_partial["method"],

            title=best_partial["title"],

            publication_date=best_partial["publication_date"],

            quality=best_partial["quality"],

        )


    print(

        f"[SCRAPER] All extraction methods failed: {url}"

    )


    return f"""

EXTRACTION_STATUS: FAILED


SOURCE_URL: {url}


ERRORS:


{chr(10).join(errors)}

"""


# ============================================================

# 14. TOOL 1: WEB SEARCH

# ============================================================


@tool

def web_search(query: str) -> str:

    """

    Search the web using Tavily.


    Returns source titles, URLs, publication dates and snippets.

    """


    try:

        if not isinstance(query, str) or not query.strip():
            return "Web search failed: query must be a non-empty string."

        if tavily is None:

            return (

                "Web search failed: "

                "TAVILY_API_KEY is missing from .env"

            )


        print(

            f"\n[SEARCH] Searching: {query}"

        )


        results = tavily.search(

            query=query,

            max_results=4,

            search_depth="basic",

            topic="general",

            include_answer=False,

            include_raw_content=False,

        )


        search_results = results.get("results", []) if isinstance(results, dict) else []

        if not isinstance(search_results, list) or not search_results:
            return "No search results found."

        # Ignore malformed results and non-HTTP(S) links.
        search_results = [
            item for item in search_results
            if isinstance(item, dict) and validate_url(item.get("url", ""))
        ]

        if not search_results:
            return "No usable search results with valid HTTP/HTTPS URLs were found."

        # Keep Tavily relevance primary; preferred domains break ties only.
        search_results = rank_search_results(search_results)

        output = []


        for index, result in enumerate(

            search_results,

            start=1

        ):


            url = result.get(

                "url",

                ""

            )


            domain = get_source_domain(url) or "Unknown"


            output.append(

                f"""

SOURCE {index}


Title: {result.get('title', 'Unknown')}


URL: {url}


Source Domain: {domain}


Published Date: {result.get('published_date', 'Not provided')}


Tavily Relevance Score: {result.get('score', 'Not provided')}


Snippet:

{result.get('content', '')[:350]}

"""

            )


        print(

            f"[SEARCH] Found {len(search_results)} sources."

        )


        return "\n".join(output)


    except Exception as e:


        print(

            f"[SEARCH ERROR] {e}"

        )


        return f"Web search failed: {str(e)}"


# ============================================================

# 15. TOOL 2: MULTI-LAYER SCRAPER

# ============================================================


@tool

def scrape_url(url: str) -> str:

    """

    Extract webpage content using multiple fallback methods.


    1. BeautifulSoup

    2. Trafilatura

    3. Tavily Advanced Extract

    4. Playwright + Trafilatura


    Returns extraction status, method, title, date and content.

    """


    return scrape_url_fallback(url)
