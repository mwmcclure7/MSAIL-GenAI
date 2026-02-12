from groq import Groq

client = Groq()

prompt = """
A local farmer sells two types of fruit baskets.
1. Basket A contains 3.75 apples and 2.33 oranges and costs $12.34.
2. Basket B contains 5.125 apples and 4.5 oranges and costs $23.98.
Based on these prices, what is the individual cost of one \
    apple and the individual cost of one orange?
Output only the answer. Do not provide any additional explanation.
"""

completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    model="openai/gpt-oss-20b",
    reasoning_effort="high",
    include_reasoning=True,
)

print("*** REASONING ***")
print(completion.choices[0].message.reasoning)

print("*** MESSAGE ***")
print(completion.choices[0].message.content)
