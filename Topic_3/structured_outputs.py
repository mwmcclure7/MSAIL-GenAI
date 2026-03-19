from groq import Groq
import json

groq = Groq()

response = groq.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "system", "content": "Extract product review information from the text."},
        {
            "role": "user",
            "content": "I bought the UltraSound Headphones last week and I'm really impressed! The noise cancellation is amazing and the battery lasts all day. Sound quality is crisp and clear. I'd give it 4.5 out of 5 stars.",
        },
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "product_review",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "rating": {"type": "number"},
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"]
                    },
                    "key_features": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["product_name", "rating", "sentiment", "key_features"],
                "additionalProperties": False
            }
        }
    }
)

result = json.loads(response.choices[0].message.content or "{}")

product_name = result.get("product_name")
rating       = result.get("rating")
sentiment    = result.get("sentiment")
key_features = result.get("key_features")

print(f"product_name: {product_name} | type: {type(product_name)}")
print(f"rating: {rating} | type: {type(rating)}")
print(f"sentiment: {sentiment} | type: {type(sentiment)}")
print(f"key_features: {key_features} | type: {type(key_features)}")

