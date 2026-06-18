from ollama import chat

response = chat(
    model="gemma4:12b",
    messages=[
        {
            "role": "user",
            "content": "Reply with only: OLLAMA WORKING"
        }
    ]
)

print(response.message.content)