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

def simple_query(req, output=None):
    res = client.models.generate_content(model=model, contents=req)
    if output:
        with open(output, "w") as f: f.write(res.text)
    else: print(res.text)

def start_chat(output=None):
    chat = client.chats.create(model=model)
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
    parser = argparse.ArgumentParser(description="Gemini AI Toolset")
    parser.add_argument("-m", "--models", action="store_true")
    parser.add_argument("-c", "--chat", action="store_true")
    parser.add_argument("-o", "--output")
    parser.add_argument("request", nargs='?')

    args = parser.parse_args()

    if args.models:
        get_models(args.output)
    elif args.chat:
        start_chat(args.output)
    elif args.request:
        simple_query(args.request, args.output)