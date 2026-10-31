from bot import answer

print("Hi! I'm the VIPS FAQ Bot. Ask me about attendance, timetable, fees, library, or canteen.")
print("Type 'exit' or 'quit' to stop.\n")

while True:
    question = input("You: ").strip()
    if question.lower() in ("exit", "quit"):
        print("Bot: Goodbye!")
        break
    if not question:
        continue
    print(f"Bot: {answer(question)}\n")