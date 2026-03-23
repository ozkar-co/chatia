from google import genai
import argparse
import sys

with open("key.txt") as f:
        apikey = f.read().strip()

client = genai.Client(api_key=apikey)
model = "gemini-flash-latest"

def get_models():
    for model in client.models.list():
        print(f"{model.name}:{model.supported_actions}")

def simple_query(req):
    res = client.models.generate_content(model=model,contents=req)
    print(res.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini AI Toolset")
    parser.add_argument("-m", "--models", action="store_true", help="List all available models")
    parser.add_argument("-c", "--chat", action="store_true", help="Start a chat session")
    parser.add_argument("-r", "--request", type=str, help="Query a simple request")

    args = parser.parse_args()

    if args.models:
        get_models()
    if args.chat:
        pass
    if args.request:
        simple_query(args.request)

