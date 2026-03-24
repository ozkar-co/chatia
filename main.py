from google import genai
import argparse
import sys

with open("key.txt") as f:
    apikey = f.read().strip()

client = genai.Client(api_key=apikey)
model = "gemini-flash-latest"

def get_models(output=None):
    results = [f"{m.name}:{m.supported_actions}" for m in client.models.list()]
    content = "\n".join(results)
    if output:
        with open(output, "w") as f: f.write(content)
    else: print(content)

def simple_query(req, context=None, output=None):
    config = {"system_instruction": context} if context else None
    res = client.models.generate_content(model=model, contents=req, config=config)
    if output:
        with open(output, "w") as f: f.write(res.text)
    else: print(res.text)

def start_chat(context=None, output=None):
    config = {"system_instruction": context} if context else None
    chat = client.chats.create(model=model, config=config)
    history = ""
    try:
        while (user_input := input("User: ")).lower() not in ["exit", "quit"]:
            res = chat.send_message(user_input)
            turn = f"User: {user_input}\nAI: {res.text}\n"
            print(f"AI: {res.text}")
            history += turn
    except (EOFError, KeyboardInterrupt): pass
    if output:
        with open(output, "w") as f: f.write(history)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        description="Command-line interface for interacting with Google Gemini AI.")
    parser.add_argument("-m", "--models", action="store_true", 
                        help="List all available AI models and their supported capabilities.")
    parser.add_argument("-c", "--chat", action="store_true", 
                        help="Start an interactive, multi-turn conversation session.")
    parser.add_argument("-x", "--context", 
                        help="Path to a file containing system instructions or background context.")
    parser.add_argument("-o", "--output", 
                        help="Path to a file where the output or chat history will be saved.")
    parser.add_argument("request", nargs='?', 
                        help="The prompt or query to send to the AI for single-shot execution.")

    args = parser.parse_args()

    context_text = None
    if args.context:
        with open(args.context, "r", encoding="utf-8") as f:
            context_text = f.read().strip()

    if args.models:
        get_models(args.output)
    elif args.chat:
        start_chat(context_text, args.output)
    elif args.request:
        simple_query(args.request, context_text, args.output)
