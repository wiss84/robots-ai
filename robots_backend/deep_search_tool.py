from langchain_core.tools import tool
from pydantic import BaseModel, Field
from ddgs import DDGS
import time
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import threading
from dotenv import load_dotenv
load_dotenv()

# Import URL streaming functions
from server_sent_events import add_url_to_stream, clear_url_stream, signal_stream_complete, signal_search_started

# Create current date for time-aware search queries
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# --- Setup Gemini clients ---
# Use flash-lite for query expansion (shares quota with agent)
llm_expansion = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
)

# Use full flash for batch summarization and final summary (separate quota)
llm_summarization = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)

# --- Helpers ---
def duckduckgo_search(query: str, max_results: int = 25):
    """Search DuckDuckGo with error handling."""
    try:
        with DDGS(timeout=10) as ddg:
            results = [r for r in ddg.text(
                query,
                max_results=max_results,
                safe_search='moderate',
                region='us-en',
                timelimit='y',
                # backend='bing, brave, google, mullvad_brave, mullvad_google, yahoo, yandex'
                backend='auto'
            )]
        return results
    except Exception as e:
        print(f"Search error for query '{query}': {e}")
        return []

def expand_queries_with_gemini(query: str, research_domain: str = "general"):
    """Ask Gemini to propose refined subqueries for deeper research."""
    domain_context = {
        "general": "You are a research strategist. Generate 5 diverse, high-quality search queries for comprehensive research, include the original query in the list.",
        "academic": "You are an academic research strategist. Generate 5 scholarly search queries for in-depth research, include the original query in the list.",
        "technical": "You are a technical research strategist. Generate 5 technical search queries for detailed research, include the original query in the list.",
        "business": "You are a business research strategist. Generate 5 business-focused search queries for market research, include the original query in the list.",
        "finance": "You are a financial research strategist. Generate 5 financial search queries for market research, include the original query in the list.",
        "medical": "You are a medical research strategist. Generate 5 medical/health search queries for thorough research, include the original query in the list.",
        "legal": "You are a legal research strategist. Generate 5 legal search queries for comprehensive research, include the original query in the list."
    }
    
    system_prompt = domain_context.get(research_domain, domain_context["general"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Today's date is {current_date}. When generating search queries, consider this date for any time-sensitive information, trends, or current events.\n\nOriginal query: {query}\n\nReturn only the queries as a numbered list, focusing on different aspects and perspectives of the topic. For time-sensitive queries, include recent/current variations where appropriate.")
    ])
   
    try:
        chain = prompt | llm_expansion  # Only query expansion uses flash-lite
        response = chain.invoke({"query": query, "current_date": CURRENT_DATE})
        
        # Parse numbered list into array
        lines = response.content.split("\n")
        subqueries = []
        for line in lines:
            if line.strip() and any(char.isdigit() for char in line[:5]):
                # Remove numbering and clean up
                clean_query = line.split(". ", 1)[-1].strip()
                if clean_query:
                    subqueries.append(clean_query)
        
        return subqueries[:5] if subqueries else [query]
    except Exception as e:
        print(f"Error generating subqueries: {e}")
        return [query]  # Fallback to original query


def collect_results(subqueries, max_results=25, delay=5):
    """
    Run searches for all subqueries with throttling and deduplication.
    Push each discovered URL to SSE immediately and return full results list.
    """
    all_results = []
    seen_urls = set()

    for i, sq in enumerate(subqueries):
        print(f"Searching: {sq}")
        current_delay = delay + (i * 2)
        time.sleep(current_delay)

        results = duckduckgo_search(sq, max_results=max_results)

        for result in results:
            url = (result.get("href") or "").strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(result)
                # Stream incrementally via SSE
                add_url_to_stream(url)

    return all_results


def batch_summarize(results, batch_size=25, research_domain="general"):
    """Summarize search results in batches to avoid token explosion."""
    if not results:
        return []
    
    domain_instructions = {
        "general": "You are a research analyst. Summarize key findings, keeping important facts, dates, and context. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com).",
        "academic": "You are an academic researcher. Summarize key findings with focus on methodology, conclusions, and scholarly insights. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com).",
        "technical": "You are a technical analyst. Summarize key findings with focus on specifications, implementations, and technical details. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com).",
        "business": "You are a business analyst. Summarize key findings with focus on market data, trends, and business implications. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com).",
        "finance": "You are a financial analyst. Summarize key findings with focus on financial data, market trends, and investment insights. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com).",
        "medical": "You are a medical researcher. Summarize key findings with focus on clinical data, research results, and health implications. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com).",
        "legal": "You are a legal analyst. Summarize key findings with focus on legal precedents, regulations, and case details. IMPORTANT: Always preserve and include the source URLs in your summary as plain URLs without brackets or formatting (e.g., https://example.com)."
    }
    
    system_prompt = domain_instructions.get(research_domain, domain_instructions["general"])
    
    batches = [results[i:i+batch_size] for i in range(0, len(results), batch_size)]
    summaries = []
    
    for i, batch in enumerate(batches):
        print(f"Summarizing batch {i+1}/{len(batches)}")
        
        snippets = []
        for r in batch:
            title = r.get("title", "")
            body = r.get("body", "")
            link = r.get("href", "")
            # Ensure URL is clean and properly formatted
            clean_link = link.strip()
            snippet = f"- **{title}**: {body}\nSource: {clean_link}"
            snippets.append(snippet)

        text_block = "\n".join(snippets)
        print(f"Final text block: {text_block[:300]}...")  # Debug: Check final text block
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here are search results to summarize:\n\n{text}\n\nProvide a summary highlighting the most important information and insights. For each fact or claim, include the source link as a plain URL (e.g., https://example.com) without brackets or additional formatting.")
        ])
        
        try:
            time.sleep(2)  # Rate limiting
            chain = prompt | llm_summarization  # Batch summaries use flash
            response = chain.invoke({"text": text_block})

            # Clean up Gemini's response to remove square brackets around URLs
            cleaned_content = response.content
            # Remove square brackets around URLs: [https://example.com] -> https://example.com
            import re
            cleaned_content = re.sub(r'\[(\s*https?://[^\]]+)\]', r'\1', cleaned_content)
            # Also remove any standalone brackets that might remain
            cleaned_content = re.sub(r'\[\s*\]|\[\s*https?://[^\]]*\]', '', cleaned_content)

            summaries.append(cleaned_content)
        except Exception as e:
            print(f"Error summarizing batch {i+1}: {e}")
            continue
    
    return summaries

def final_summarize(summaries, query, research_domain="general"):
    """Take multiple batch summaries and merge into one comprehensive answer using gemini-2.0-flash."""
    if not summaries:
        return "No information could be processed."
    
    joined = "\n\n".join(summaries)
    print(f"Joined summaries preview: {joined[:500]}...")  # Debug: Check joined summaries

    domain_context = {
        "general": "comprehensive research report",
        "academic": "academic research with scholarly insights",
        "technical": "technical analysis with detailed specifications",
        "business": "business intelligence report with market insights",
        "finance": "financial analysis report with market data and insights",
        "medical": "medical research with clinical findings",
        "legal": "legal analysis with regulatory and case law insights"
    }
    
    report_type = domain_context.get(research_domain, domain_context["general"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an expert research analyst. Create a {report_type} that synthesizes information from multiple sources."),
        ("human", """Today's date is {current_date}. Use this date context when analyzing trends, recent developments, and time-sensitive information.

Original query: {query}

Research summaries from multiple searches:
{summaries}

Please create a very comprehensive, well-structured final report that:
1. Directly addresses the original query
2. Synthesizes the key findings from all sources
3. Identifies patterns, trends, or insights (considering current date context for relevance)
4. Highlights recent developments and current market conditions where applicable
5. Provides a clear, time-aware conclusion
6. Always preserve and include source links as plain URLs (e.g., https://example.com) without any brackets, formatting, or additional text.

IMPORTANT: Include source URLs as plain links like "Source: https://example.com" at the end of relevant paragraphs or sections. Do not wrap URLs in brackets, quotes, or any other formatting.

Structure your response with clear headings and organize the information logically. For time-sensitive queries, emphasize recent data and current trends.""")
    ])
    
    try:
        time.sleep(5)  # Rate limiting
        chain = prompt | llm_summarization  # Final summary also uses flash
        response = chain.invoke({"summaries": joined, "query": query, "current_date": CURRENT_DATE})

        # Clean up Gemini's response to remove square brackets around URLs
        cleaned_content = response.content
        import re
        cleaned_content = re.sub(r'\[(\s*https?://[^\]]+)\]', r'\1', cleaned_content)
        # Also remove any standalone brackets that might remain
        cleaned_content = re.sub(r'\[\s*\]|\[\s*https?://[^\]]*\]', '', cleaned_content)

        return cleaned_content
    except Exception as e:
        print(f"Error in final summarization: {e}")
        return f"Error generating final summary. Raw summaries: {joined}"

# --- Input Schema ---
class DeepSearchInput(BaseModel):
    query: str = Field(..., description="The research query to search for comprehensively.")
    research_domain: str = Field(
        default="general", 
        description="Research domain: general, academic, technical, business, finance, medical, or legal"
    )
    max_results_per_query: int = Field(
        default=25, 
        description="Maximum results per subquery (default: 25)"
    )

# --- LangChain Tool ---
@tool("deep_search", args_schema=DeepSearchInput, return_direct=False)
def deep_search(query: str, research_domain: str = "general", max_results_per_query: int = 25) -> str:
    """
    Comprehensive deep web search with progressive URL streaming via SSE.
    """
    print(f"Starting deep search for: {query}")
    print(f"Research domain: {research_domain}")

    # Clear SSE queue for a fresh run
    clear_url_stream()
    
    # Signal that deep search has started
    signal_search_started()

    # 1) Expand subqueries
    subqueries = expand_queries_with_gemini(query, research_domain)
    print(f"Generated {len(subqueries)} subqueries")

    # 2) Collect results in a background thread so SSE can flush concurrently
    results_container = {"all_results": []}

    def run_collection():
        results_container["all_results"] = collect_results(
            subqueries,
            max_results=max_results_per_query,
            delay=3
        )

    t = threading.Thread(target=run_collection, daemon=True)
    t.start()
    t.join()  # We still return the final answer only after collection completes

    all_results = results_container["all_results"]
    print(f"Found {len(all_results)} unique results")

    if not all_results:
        return f"No relevant results found for query: {query}"

    # 3) Summarize and synthesize (unchanged)
    batch_summaries = batch_summarize(all_results, batch_size=25, research_domain=research_domain)
    print(f"Generated {len(batch_summaries)} batch summaries")

    if not batch_summaries:
        return "Unable to process search results."

    final_answer = final_summarize(batch_summaries, query, research_domain)
    print(f"Final answer preview: {final_answer[:300]}...")
    
    # Signal completion to terminate SSE stream
    signal_stream_complete()
    
    return final_answer