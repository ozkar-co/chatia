import sys
from pathlib import Path

DOCS_DIR = Path.home() / "docs"
KEY_FILE = DOCS_DIR / "key.txt"
CHATS_DIR = DOCS_DIR / "chats"


def load_api_key() -> str:
    if not KEY_FILE.is_file():
        print(f"Error: no se encontró la API key en '{KEY_FILE}'", file=sys.stderr)
        sys.exit(1)
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        print(f"Error: '{KEY_FILE}' está vacío", file=sys.stderr)
        sys.exit(1)
    return key
