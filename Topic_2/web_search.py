from groq import Groq

client = Groq()

completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "What is MSAIL at the University of Michigan?"
        }
    ],
    model="openai/gpt-oss-20b",
    tool_choice="required",
    tools=[
        {
            "type": "browser_search"
        }
    ],
)

print("*** MESSAGE ***")
print(completion.choices[0].message.content)

# Note that reasoning is used automatically for GPT-OSS models
print("*** REASONING ***")
print(completion.choices[0].message.reasoning)

print("*** EXECUTED TOOLS ***")
print(completion.choices[0].message.executed_tools[0])
