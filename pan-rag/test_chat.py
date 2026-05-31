# test_chat.py
import requests

API_URL = "http://localhost:8000/api/ask"

print("=" * 50)
print("  PAN Card Assistant — type 'quit' to exit")
print("=" * 50 + "\n")

session_id = None
user_id = "test_user"

while True:
    question = input("You: ").strip()

    if question.lower() == "quit":
        print("Goodbye! 😊")
        break

    if not question:
        continue

    print("Thinking... 💭\n")

    response = requests.post(API_URL, json={
        "question": question,
        "session_id": session_id,
        "user_id": user_id
    })

    result = response.json()
    session_id = result.get("session_id", session_id)

    print(f"Bot: {result.get('answer', 'Sorry, something went wrong.')}\n")

    # Show followup suggestions
    followups = result.get("followups", [])
    if followups:
        print("💡 You can also ask:")
        for i, f in enumerate(followups, 1):
            print(f"   {i}. {f}")
        print()