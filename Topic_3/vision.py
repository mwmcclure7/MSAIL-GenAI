from groq import Groq

client = Groq()
completion = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What's in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://msail.github.io/logo-M.png"
                    }
                }
            ]
        }
    ]
)

print(completion.choices[0].message.content)

