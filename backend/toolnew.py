
from langchain.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


@tool
def web_search(query: str) -> str:
    """
    Search the web for recent and reliable information.
    Returns structured results with titles, URLs,
    descriptions and relevance scores.
    """

    try:
        response = tavily.search(
            query=query,
            topic="news",
            time_range="month",
            max_results=5,
            search_depth="advanced"
        )

        results = response.get("results", [])

        if not results:
            return "No search results found."

        output = []

        output.append("=" * 70)
        output.append("WEB SEARCH RESULTS")
        output.append("=" * 70)
        output.append(f"\nSearch Query: {query}")
        output.append(f"Total Results: {len(results)}\n")

        for index, result in enumerate(results, start=1):

            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            content = result.get("content", "No description")
            score = result.get("score", 0)

            output.append("-" * 70)
            output.append(f"RESULT {index}")
            output.append("-" * 70)

            output.append(f"Title       : {title}")
            output.append(f"URL         : {url}")
            output.append(f"Relevance   : {score:.2f}")
            output.append(f"\nDescription:\n{content}\n")

        output.append("=" * 70)
        output.append("END OF SEARCH RESULTS")
        output.append("=" * 70)

        return "\n".join(output)

    except Exception as e:
        return f"Web search error: {str(e)}"


if __name__ == "__main__":

    result = web_search.invoke(
        "Recent NVIDIA company news"
    )

    print(result)
