import os
import json
import yfinance as yf
from groq import Groq

# Initialize the Groq client
client = Groq()
MODEL = "openai/gpt-oss-20b"

def get_stock_info(ticker):
    """Fetch current stock info and historical data using Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        
        # Package only the essential data to avoid blowing up the context window
        data = {
            "symbol": ticker.upper(),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
            "forward_pe": info.get("forwardPE"),
            "market_cap": info.get("marketCap"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "analyst_recommendation": info.get("recommendationKey"),
            "last_5_days_close_prices": hist['Close'].tolist()[-5:] if not hist.empty else []
        }
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch data for {ticker}: {str(e)}"})

def analyze_stock(ticker):
    """Run the agentic conversation with tool calling."""
    print(f"Analyzing {ticker.upper()}... Please wait.\n")
    
    messages = [
        {
            "role": "system",
            "content": """You are an expert quantitative financial analyst. Perform the following steps:
                1. Call the `get_stock_info` function to get foundational Yahoo Finance data.
                2. Search the web to find recent news, earnings reports, and overall market sentiment.
                3. Write and execute Python code to calculate standard metrics like short-term volatility or moving
                averages based on the retrieved data.
                4. Output a final prediction on how the stock will move over the following timeframes:
                next day, next week, next month, next six months, and next year.
                5. For your final response, respond only in plain text. Do not use any markdown.
                Important: Rely on your native capabilities for web searches and code execution.
                Do not attempt to call them as custom functions."""
        },
        {
            "role": "user",
            "content": f"Please analyze {ticker.upper()} and generate your timeframe predictions.",
        }
    ]
    
    tools = [
        {"type": "browser_search"},
        {"type": "code_interpreter"},
        {
            "type": "function",
            "function": {
                "name": "get_stock_info",
                "description": "Get current stock information and historical pricing data using Yahoo Finance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "The stock ticker symbol (e.g., AAPL)"
                        }
                    },
                    "required": ["ticker"],
                },
            },
        }
    ]
    
    available_functions = {
        "get_stock_info": get_stock_info,
    }

    # Step 1: Initial API Call
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        reasoning_effort="high"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    
    # Step 2: Check for and execute local tool calls
    if tool_calls:
        messages.append(response_message)
        
        for tool_call in tool_calls:
            # Safety check to ensure we only process custom local functions
            if tool_call.type == "function":
                function_name = tool_call.function.name
                
                if function_name in available_functions:
                    print(f"-> Executing local tool: {function_name}()")
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    
                    function_response = function_to_call(
                        ticker=function_args.get("ticker")
                    )
                    
                    # Append local tool response to conversation
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
        
        # Step 3: Second pass to Groq to ingest local data and finish analysis
        print("-> Generating final prediction (this may take a moment for high reasoning)...\n")
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools, 
            reasoning_effort="high"
        )
        final_message = final_response.choices[0].message
    else:
        final_message = response_message

    # Step 4: Output the results
    print("="*60)
    
    if hasattr(final_message, 'reasoning') and final_message.reasoning:
        print("*** REASONING ***")
        print(final_message.reasoning)
        print("-" * 60)
        
    print("*** PREDICTION ***")
    print(final_message.content)
    
    if hasattr(final_message, 'executed_tools') and final_message.executed_tools:
        print("\n*** EXECUTED BUILT-IN TOOLS ***")
        for tool in final_message.executed_tools:
            print(f"- {tool.name}")


if __name__ == "__main__":
    target_ticker = input("Enter a stock ticker (e.g., TSLA, NVDA): ")
    analyze_stock(target_ticker)