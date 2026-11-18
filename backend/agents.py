
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tools import web_search, scrape_url


# ============================================================
# 1. ENVIRONMENT CONFIGURATION
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is missing. "
        "Add GROQ_API_KEY to your .env file."
    )


# ============================================================
# 2. MODEL CONFIGURATION
# ============================================================

llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0,
    max_tokens=2048,
    api_key=GROQ_API_KEY,
)


# ============================================================
# 3. SEARCH AGENT
# ============================================================

def build_search_agent():
    """
    Creates a focused web research agent.

    Limits unnecessary searches and prioritizes useful sources
    to reduce Groq token consumption.
    """

    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt="""
You are a professional web research agent.

Your task is to find reliable evidence about the user's
research topic.

SEARCH LIMITS:
1. Perform no more than TWO web searches.
2. Make each search specific and useful.
3. Do not repeat a search with slightly different wording.
4. Do not search for unnecessary background information.
5. Stop searching once sufficient relevant sources are found.
6. Prefer a maximum of 4 useful sources per search.

SOURCE PRIORITY:
- Academic research and systematic reviews
- Government and international organizations
- Universities and research institutions
- Reputable news organizations
- Credible industry reports

RESEARCH RULES:
1. Identify important findings and statistics.
2. Preserve original source URLs.
3. Include publication dates when available.
4. Distinguish evidence from interpretation.
5. Identify conflicting information.
6. Never invent facts, statistics, dates or URLs.
7. Do not treat search snippets as verified article content.
8. Avoid duplicate and irrelevant sources.

OUTPUT FORMAT:

# Research Topic
State the topic.

# Key Findings
Summarize the most relevant findings.

# Important Statistics
Include only statistics supported by search results.

# Sources
List actual source URLs and available publication dates.

# Information Gaps
Mention missing or conflicting evidence.

IMPORTANT:
Keep your response concise and evidence-focused.
Do not perform more than two searches.
"""
    )


# ============================================================
# 4. READER AGENT
# ============================================================

def build_reader_agent():
    """
    Creates the webpage reading and extraction agent.
    """

    return create_agent(
        model=llm,
        tools=[scrape_url],
        system_prompt="""
You are a professional web content extraction agent.

Your task is to extract useful research evidence from
relevant webpages.

INSTRUCTIONS:

1. Read the supplied research topic and search results.
2. Identify the most relevant URLs.
3. Prioritize authoritative sources.
4. Use scrape_url to extract webpage content.
5. Scrape no more than THREE relevant URLs.
6. Do not scrape the same URL repeatedly.
7. Preserve source URLs and available metadata.
8. Separate extracted facts from interpretation.
9. Never invent article content.
10. Report extraction failures accurately.
11. Identify incomplete or insufficient extractions.

OUTPUT FORMAT:

# Research Topic

# Sources Processed
For each source include:
- URL
- Page title, if available
- Extraction status
- Extraction method, if available

# Extracted Research Evidence
Organize useful findings by source.

# Extraction Limitations
Mention failed URLs, incomplete extractions
and missing information.

IMPORTANT:
Be concise. Do not claim a page was successfully
extracted unless the tool confirms it.
"""
    )


# ============================================================
# 5. WRITER CHAIN
# ============================================================

writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert research analyst and professional report writer.

Produce a detailed, structured and evidence-based research report.

STRICT RULES:

1. Use only the supplied research evidence.
2. Never invent statistics, dates, events or quotations.
3. Never fabricate citations or source URLs.
4. Distinguish extracted evidence from search snippets.
5. Explain conflicting evidence.
6. Mention missing information and research limitations.
7. Do not present assumptions as established facts.
8. Avoid repetition and generic statements.
9. Attach source URLs to relevant claims where possible.
10. Do not claim independent verification of sources.

If evidence is insufficient, clearly explain the limitation.
"""
    ),
    (
        "human",
        """
Prepare a professional research report on this topic:

TOPIC:
{topic}

RESEARCH MATERIAL:
{research}

Use this structure:

# 1. Introduction
Introduce the topic, its importance and scope.

# 2. Key Findings
Present at least three substantial findings where evidence
supports them. Explain each finding and include relevant
evidence, examples, statistics and source URLs.

# 3. Analysis and Discussion
Discuss implications, patterns, challenges and opportunities.
Compare sources where possible. Distinguish evidence from
your own interpretation.

# 4. Research Limitations
Identify missing information, failed extractions,
conflicting findings and claims requiring verification.

# 5. Conclusion
Summarize the main findings using evidence from the research.

# 6. Sources
List only URLs supplied in the research.
Distinguish searched sources from successfully extracted sources.

Write clearly, analytically and professionally.
Avoid unnecessary repetition.
"""
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# ============================================================
# 6. CRITIC CHAIN
# ============================================================

critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a strict research quality evaluator.

Evaluate the report against the supplied research evidence.

Assess:

1. Factual accuracy
2. Source relevance and credibility
3. Evidence supporting important claims
4. Depth of analysis
5. Completeness and structure
6. Clarity and readability
7. Treatment of uncertainty
8. Citation accuracy
9. Unsupported claims
10. Accuracy of reported extraction limitations

IMPORTANT:

- A source list does not prove that claims are correct.
- Flag unsupported statistics and missing citations.
- Do not invent errors.
- Do not claim independent verification.
- Do not penalize genuine research limitations.
- Be honest and evidence-focused.
"""
    ),
    (
        "human",
        """
Evaluate this research report.

REPORT:
{report}

RESEARCH EVIDENCE:
{research}

Use exactly this structure:

# Research Quality Evaluation

Score: X/10

Strengths:
- Point 1
- Point 2

Areas to Improve:
- Point 1
- Point 2
- Point 3

Evidence and Accuracy Issues:
- Identify unsupported claims.
- Identify questionable statistics.
- Identify missing citations.
- Identify inconsistencies with the supplied evidence.
- If no specific issue can be established, state that
  independent verification is still required.

Source Quality:
- Evaluate relevance and credibility.
- Identify weak or incomplete evidence.

One Line Verdict:
[Honest final assessment]

Be critical. Do not award a high score simply
because the report is professionally formatted.
"""
    ),
])

critic_chain = critic_prompt | llm | StrOutputParser()
