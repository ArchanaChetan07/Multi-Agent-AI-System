import os
from dotenv import load_dotenv
from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo

# Load environment variables
load_dotenv()

# Access keys
groq_key = os.getenv('GROQ_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')
phi_key = os.getenv('PHI_API_KEY')

# Debug: Print the keys (remove in production)
print(f"Groq Key: {groq_key}")
print(f"OpenAI Key: {openai_key}")
print(f"Phi Key: {phi_key}")

# Web Search Agent
web_search_agent = Agent(
    name="Web Search Agent",
    role="Search the web for the information",
    model=Groq(id="gpt-3.5-turbo"),  # Use a valid model ID
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)

# Financial Agent
finance_agent = Agent(
    name="Finance AI Agent",
    model=Groq(id="gpt-3.5-turbo"),  # Use a valid model ID
    tools=[
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            stock_fundamentals=True,
            company_news=True,
        )
    ],
    instructions=["Use tables to display the data"],
    show_tool_calls=True,
    markdown=True,
)

# Multi-Agent Setup
multi_ai_agent = Agent(
    team=[web_search_agent, finance_agent],
    instructions=["Always include sources", "Use tables to display the data"],
    show_tool_calls=True,
    markdown=True,
)

# Test Query
try:
    multi_ai_agent.print_response(
        "Summarize analyst recommendation and share the latest news for NVDA", stream=True
    )
except Exception as e:
    print(f"Error: {e}")