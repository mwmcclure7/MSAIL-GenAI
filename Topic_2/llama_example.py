from groq import Groq

client = Groq()

prompt = """
A local farmer sells two types of fruit baskets.
1. Basket A contains 3 apples and 2 oranges and costs $12.
2. Basket B contains 5 apples and 4 oranges and costs $22.
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
    model="llama-3.3-70b-versatile",
)

print("*** MESSAGE ***")
print(completion.choices[0].message.content)
