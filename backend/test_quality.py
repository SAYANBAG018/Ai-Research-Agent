
from research_quality import (
    rank_search_results,
    print_quality_report
)

query = "Artificial intelligence research breakthroughs and model releases November 2026"

results = [
    {
        "title": "Claude Platform release notes",
        "url": "https://platform.claude.com/docs/en/release-notes/overview",
        "published_date": "12 November 2026",
        "snippet": "Anthropic launched Claude Fable 5.2 and Claude Mythos 5.2."
    },
    {
        "title": "New AI Models in November 2026",
        "url": "https://beevr.ai/blog/ai-model-releases-november-2026",
        "published_date": "13 November 2026",
        "snippet": "A roundup of new model releases in November 2026."
    },
    {
        "title": "Artificial Intelligence Nov 2026",
        "url": "https://arxiv.org/list/cs.AI/current",
        "published_date": None,
        "snippet": "Current artificial intelligence research papers."
    },
    {
        "title": "AI discussion and opinions",
        "url": "https://www.reddit.com/",
        "published_date": None,
        "snippet": "Community discussion about artificial intelligence."
    }
]

report = rank_search_results(results, query)
print_quality_report(report)
