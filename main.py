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
        with open(output, "w") as f:
            f.write(content)
    else:
        print(content)

def simple_query(req, output=None):
    res = client.models.generate_content(model=model, contents=req)
    if output:
        with open(output, "w") as f:
            f.write(res.text)
    else:
        print(res.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini AI Toolset")
    parser.add_argument("-m", "--models", action="store_true", help="List all available models")
    parser.add_argument("-c", "--chat", action="store_true", help="Start a chat session")
    parser.add_argument("-o", "--output", help="Output file to store the answer")
    parser.add_argument("request", type=str, nargs='?', help="the to request to make")

    args = parser.parse_args()

    if args.models:
        get_models(args.output)
    if args.chat:
        pass
    if args.request:
        simple_query(args.request, args.output)
