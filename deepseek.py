import json
import urllib.error
import urllib.request

API_URL = "https://api.deepseek.com/chat/completions"
MODELS = {"flash": "deepseek-flash", "pro": "deepseek-v4-pro"}


class DeepSeekError(Exception):
    pass


def stream(api_key: str, model: str, messages: list[dict]):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "thinking": {"type": "disabled"},
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        response = urllib.request.urlopen(request, timeout=120)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise DeepSeekError(f"HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise DeepSeekError(f"No se pudo conectar: {error.reason}") from error

    with response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if data == "[DONE]":
                return
            chunk = json.loads(data)
            choices = chunk.get("choices")
            if not choices:
                continue
            text = choices[0].get("delta", {}).get("content")
            if text:
                yield text
