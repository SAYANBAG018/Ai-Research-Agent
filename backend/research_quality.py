
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


# ============================================================
# SOURCE CLASSIFICATION
# ============================================================

PRIMARY_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "ai.google",
    "blog.google",
    "nvidia.com",
    "research.google",
    "microsoft.com",
    "ai.meta.com",
    "about.fb.com",
    "huggingface.co",
    "arxiv.org",
    "nature.com",
    "science.org",
    "aclanthology.org",
    "proceedings.neurips.cc",
    "proceedings.mlr.press",
    "icml.cc",
    "openreview.net",
}

REPUTABLE_NEWS_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "ft.com",
    "technologyreview.com",
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "bloomberg.com",
}

AGGREGATOR_DOMAINS = {
    "llm-stats.com",
    "llm-releases.com",
    "llmgateway.io",
    "opper.ai",
    "local-ai-zone.github.io",
    "beevr.ai",
    "superindex.app",
    "nhimg.org",
}

# Domains that should not automatically receive high trust.
LOW_CONFIDENCE_DOMAINS = {
    "medium.com",
    "linkedin.com",
    "quora.com",
    "reddit.com",
    "youtube.com",
}


# ============================================================
# TEXT UTILITIES
# ============================================================

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "to", "of",
    "in", "on", "at", "by", "with", "from", "about", "into",
    "is", "are", "was", "were", "be", "been", "being",
    "what", "when", "where", "who", "why", "how",
    "latest", "recent", "new", "updates", "today",
    "november", "2026",
}


def normalize_domain(url):
    """Return a normalized hostname from a URL."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().strip(".")
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def domain_matches(domain, known_domain):
    """Match exact domains and their subdomains."""
    return domain == known_domain or domain.endswith("." + known_domain)


def tokenize(text):
    """Convert text into useful lowercase terms."""
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return {
        word for word in words
        if len(word) > 2 and word not in STOPWORDS
    }


# ============================================================
# DOMAIN CLASSIFICATION
# ============================================================

def classify_domain(url):
    domain = normalize_domain(url)

    for known in PRIMARY_DOMAINS:
        if domain_matches(domain, known):
            return "PRIMARY_SOURCE"

    for known in REPUTABLE_NEWS_DOMAINS:
        if domain_matches(domain, known):
            return "REPUTABLE_NEWS"

    for known in AGGREGATOR_DOMAINS:
        if domain_matches(domain, known):
            return "AGGREGATOR"

    for known in LOW_CONFIDENCE_DOMAINS:
        if domain_matches(domain, known):
            return "COMMUNITY_OR_OPINION"

    return "UNKNOWN"


# ============================================================
# DATE PARSING
# ============================================================

def parse_publication_date(value):
    """
    Parse common date formats.
    Returns timezone-aware datetime or None.

    Missing dates are not guessed.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


# ============================================================
# RELEVANCE SCORING
# ============================================================

def calculate_relevance(query, title, snippet):
    """
    Basic lexical relevance score from 0 to 5.

    This is not semantic similarity. It is a lightweight filter.
    """
    query_terms = tokenize(query)
    if not query_terms:
        return 2.5, []

    title_terms = tokenize(title)
    snippet_terms = tokenize(snippet)

    # Title matches receive more weight than snippet matches.
    title_matches = query_terms.intersection(title_terms)
    snippet_matches = query_terms.intersection(snippet_terms)

    weighted_matches = (
        len(title_matches) * 2
        + len(snippet_matches - title_matches)
    )

    maximum = len(query_terms) * 2
    score = (weighted_matches / maximum) * 5 if maximum else 0

    matched_terms = sorted(title_matches | snippet_matches)

    return round(min(score, 5), 2), matched_terms


# ============================================================
# EVIDENCE TYPE SCORING
# ============================================================

def classify_evidence(source_type, title, url):
    title_lower = (title or "").lower()
    url_lower = (url or "").lower()

    if source_type == "PRIMARY_SOURCE":
        if "arxiv.org/abs/" in url_lower:
            return "RESEARCH_PAPER", 5

        if any(word in title_lower for word in [
            "research paper",
            "technical report",
            "system card",
            "white paper",
            "benchmark",
        ]):
            return "TECHNICAL_DOCUMENT", 5

        return "OFFICIAL_ANNOUNCEMENT", 4.5

    if source_type == "REPUTABLE_NEWS":
        return "INDEPENDENT_REPORTING", 4

    if source_type == "AGGREGATOR":
        return "AGGREGATED_INFORMATION", 2

    if source_type == "COMMUNITY_OR_OPINION":
        return "COMMUNITY_OR_OPINION", 1

    return "UNCLASSIFIED", 2


# ============================================================
# FRESHNESS SCORING
# ============================================================

def calculate_freshness(publication_date, now=None):
    """
    Score freshness from 0 to 5.

    This uses publication date, not crawl date.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if publication_date is None:
        return None, "DATE_NOT_PROVIDED"

    age_days = (now - publication_date).total_seconds() / 86400

    if age_days < -1:
        return 0, "FUTURE_DATE_OR_INVALID_METADATA"

    if age_days <= 7:
        score = 5
    elif age_days <= 30:
        score = 4
    elif age_days <= 90:
        score = 3
    elif age_days <= 365:
        score = 2
    else:
        score = 1

    return score, f"{max(0, int(age_days))}_DAYS_OLD"


# ============================================================
# MAIN SOURCE EVALUATION
# ============================================================

def evaluate_source(result, query, now=None):
    """
    Evaluate one search result.

    Expected result keys:
        title
        url
        domain (optional)
        published_date
        snippet

    Returns a structured quality report.
    """

    if not isinstance(result, dict):
        result = {}

    title = str(result.get("title", "") or "")
    url = str(result.get("url", "") or "")
    snippet = str(result.get("snippet", "") or "")

    domain = normalize_domain(url)
    source_type = classify_domain(url)

    relevance_score, matched_terms = calculate_relevance(
        query, title, snippet
    )

    evidence_type, evidence_score = classify_evidence(
        source_type, title, url
    )

    publication_date = parse_publication_date(
        result.get("published_date")
    )

    freshness_score, freshness_status = calculate_freshness(
        publication_date, now
    )

    domain_scores = {
        "PRIMARY_SOURCE": 5,
        "REPUTABLE_NEWS": 4,
        "AGGREGATOR": 2,
        "COMMUNITY_OR_OPINION": 1,
        "UNKNOWN": 2.5,
    }

    domain_score = domain_scores.get(source_type, 2.5)

    # Weighted score. If date is missing, redistribute its weight
    # across the other dimensions rather than treating it as stale.
    weights = {
        "domain": 0.30,
        "relevance": 0.30,
        "freshness": 0.20,
        "evidence": 0.20,
    }

    if freshness_score is None:
        weights = {
            "domain": 0.375,
            "relevance": 0.375,
            "freshness": 0,
            "evidence": 0.25,
        }
        freshness_for_total = 0
    else:
        freshness_for_total = freshness_score

    total_score = (
        domain_score * weights["domain"]
        + relevance_score * weights["relevance"]
        + freshness_for_total * weights["freshness"]
        + evidence_score * weights["evidence"]
    )

    warnings = []

    if not url:
        warnings.append("MISSING_URL")

    if not title:
        warnings.append("MISSING_TITLE")

    if not snippet:
        warnings.append("MISSING_SNIPPET")

    if publication_date is None:
        warnings.append("PUBLICATION_DATE_UNKNOWN")

    if source_type == "AGGREGATOR":
        warnings.append("AGGREGATOR_REQUIRES_PRIMARY_SOURCE_CHECK")

    if source_type == "COMMUNITY_OR_OPINION":
        warnings.append("NOT_SUFFICIENT_AS_FINAL_EVIDENCE")

    if source_type == "UNKNOWN":
        warnings.append("DOMAIN_NOT_CLASSIFIED")

    if relevance_score < 2:
        warnings.append("LOW_QUERY_RELEVANCE")

    if freshness_status == "FUTURE_DATE_OR_INVALID_METADATA":
        warnings.append("CHECK_PUBLICATION_DATE")

    # Conservative eligibility rules.
    if (
        source_type in {"PRIMARY_SOURCE", "REPUTABLE_NEWS"}
        and relevance_score >= 2.5
        and evidence_score >= 4
        and total_score >= 3.3
    ):
        recommendation = "USE_AS_EVIDENCE"

    elif (
        source_type == "AGGREGATOR"
        and relevance_score >= 3
        and total_score >= 2.5
    ):
        recommendation = "DISCOVERY_ONLY"

    else:
        recommendation = "REVIEW_OR_REJECT"

    return {
        "title": title,
        "url": url,
        "domain": domain,
        "source_type": source_type,
        "evidence_type": evidence_type,
        "publication_date": (
            publication_date.date().isoformat()
            if publication_date else None
        ),
        "scores": {
            "domain": round(domain_score, 2),
            "relevance": relevance_score,
            "freshness": freshness_score,
            "evidence": evidence_score,
            "total": round(total_score, 2),
        },
        "matched_query_terms": matched_terms,
        "freshness_status": freshness_status,
        "recommendation": recommendation,
        "warnings": warnings,
    }


# ============================================================
# RANK AND FILTER SEARCH RESULTS
# ============================================================

def rank_search_results(results, query, now=None):
    """
    Evaluate and rank a list of search results.

    Returns:
        {
            "accepted": [...],
            "discovery_only": [...],
            "rejected": [...]
        }
    """

    evaluated = [
        evaluate_source(result, query, now)
        for result in results
    ]

    evaluated.sort(
        key=lambda item: item["scores"]["total"],
        reverse=True
    )

    return {
        "accepted": [
            item for item in evaluated
            if item["recommendation"] == "USE_AS_EVIDENCE"
        ],
        "discovery_only": [
            item for item in evaluated
            if item["recommendation"] == "DISCOVERY_ONLY"
        ],
        "rejected": [
            item for item in evaluated
            if item["recommendation"] == "REVIEW_OR_REJECT"
        ],
        "all_results": evaluated,
    }


# ============================================================
# URL-ONLY SOURCE VALIDATION (PIPELINE COMPATIBILITY)
# ============================================================

def validate_sources(urls):
    """
    Validate a list of source URLs using domain classification.

    This function is used by pipeline.py, which currently passes
    URLs only (without titles, snippets, or publication dates).

    IMPORTANT:
    This is a lightweight domain-based screening step. It does not
    fetch webpages and does not prove that a source is accurate,
    relevant, or trustworthy. Those checks require page content
    and evidence review.

    Returns a list of dictionaries with the fields expected by
    pipeline.py: domain, category, and score.
    """

    if not urls:
        return []

    validated = []
    seen = set()

    category_scores = {
        "PRIMARY_SOURCE": 9.0,
        "REPUTABLE_NEWS": 8.0,
        "AGGREGATOR": 4.0,
        "COMMUNITY_OR_OPINION": 3.0,
        "UNKNOWN": 5.0,
        "INVALID_URL": 0.0,
    }

    category_labels = {
        "PRIMARY_SOURCE": "Primary source",
        "REPUTABLE_NEWS": "Reputable news",
        "AGGREGATOR": "Aggregator",
        "COMMUNITY_OR_OPINION": "Community/opinion",
        "UNKNOWN": "Unclassified source",
        "INVALID_URL": "Invalid URL",
    }

    for raw_url in urls:
        url = str(raw_url or "").strip()

        if not url or url in seen:
            continue

        seen.add(url)

        parsed = urlparse(url)
        is_valid = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )

        if not is_valid:
            source_type = "INVALID_URL"
            domain = ""
            warnings = ["URL_IS_NOT_VALID_HTTP_OR_HTTPS"]
        else:
            domain = normalize_domain(url)
            source_type = classify_domain(url)
            warnings = []

            if source_type == "UNKNOWN":
                warnings.append("DOMAIN_NOT_CLASSIFIED")
            elif source_type == "AGGREGATOR":
                warnings.append(
                    "AGGREGATOR_REQUIRES_PRIMARY_SOURCE_CHECK"
                )
            elif source_type == "COMMUNITY_OR_OPINION":
                warnings.append(
                    "NOT_SUFFICIENT_AS_FINAL_EVIDENCE"
                )

        validated.append({
            "url": url,
            "domain": domain,
            "category": category_labels[source_type],
            "source_type": source_type,
            "score": category_scores[source_type],
            "warnings": warnings,
            "validation_method": "URL_DOMAIN_CLASSIFICATION_ONLY",
            "note": (
                "Domain classification is a screening heuristic, "
                "not factual verification or proof of article quality."
            ),
        })

    return validated



# ============================================================
# CONSOLE REPORT
# ============================================================

def print_quality_report(report):
    print("\n" + "=" * 65)
    print("RESEARCH SOURCE QUALITY REPORT")
    print("=" * 65)

    for section in ["accepted", "discovery_only", "rejected"]:
        items = report[section]

        print(f"\n{section.upper().replace('_', ' ')}: {len(items)}")

        for index, item in enumerate(items, start=1):
            print(f"\n{index}. {item['title']}")
            print(f"   Domain: {item['domain']}")
            print(f"   Type: {item['source_type']}")
            print(f"   Evidence: {item['evidence_type']}")
            print(f"   Date: {item['publication_date']}")
            print(f"   Scores: {item['scores']}")
            print(f"   Decision: {item['recommendation']}")

            if item["warnings"]:
                print(f"   Warnings: {', '.join(item['warnings'])}")
