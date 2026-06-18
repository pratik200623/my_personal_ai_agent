from ollama import chat

response = chat(
    model="gemma4:12b", #you can change the model as per your system 
    messages=[
        {
            "role": "user",
            "content": "Reply with only: OLLAMA WORKING"
        }
    ]
)

print(response.message.content)
