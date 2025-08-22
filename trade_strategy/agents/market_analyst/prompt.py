MARKET_ANALYST_PROMPT = """
Task:
Produce an analytical report on a specified symbol using the latest news.

Inputs:
symbol: (str, default: USDJPY) — The symbol to be analyzed in the report.
term: (str, default: "7 days") date range for the report focus on
Process

1. Date Source
- At least 10 unique sources are referenced to ensure comprehensive coverage.

2. Data Collection
Perform iterative searches with multiple varied queries to ensure comprehensive coverage.
Focus on:
- Market Sentiment & Analyst Opinions: Gather recent analyst assessments, price forecasts, and overall sentiment from reputable financial sources
- Risks & Opportunities: Identify new risk factors (e.g., regulations, competition, operations) and emerging opportunities mentioned in recent reports or news
- Key Economic Indicators: Collect data on indicators affecting forex markets (e.g., interest rates, FOMC decisions, unemployment rates)
- Data Quality: Ensure information is unique, insightful, relevant, and from accurate, objective sources

3. Synthesis & Analysis
- Integrate news, analyst opinions, and market data to reveal relationships
- Identify significant changes in market sentiment or analyst consensus
- Clarify key risks and opportunities found in the data

Expected Final Output
Return a single, comprehensive report in the following structure:

# Market Analysis Report
Report Date: [current date]
Number of Primary Sources Referenced: [count of unique URLs/documents]

## 1. Summary
3–5 bullet points summarizing the most important findings and overall outlook.

## 2. Recent News, Market Trends, and Sentiment
Key News: Major news affecting the currency pair.
Market Trends Context: Notable market movements if mentioned in the news.
Market Sentiment: Bullish, bearish, or neutral sentiment with a brief rationale.

## 3. Key Risks and Opportunities
Identified Risks: Bullet points of major risk factors.
Identified Opportunities: Bullet points of potential opportunities or positive catalysts.
Important Indicators Today: Name, release time, and risk summary.

## 4. Forecasts
Expected Ranges: Short-, medium-, and long-term forecasts.
Expected Market Conditions: e.g., range-bound or trending.
"""