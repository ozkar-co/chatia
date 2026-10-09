from google import genai
import argparse
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.style import Style

# Leer API Key
try:
    with open("key.txt") as f:
        apikey = f.read().strip()
except FileNotFoundError:
    print("Error: No se encontró el archivo 'key.txt'")
    sys.exit(1)

client = genai.Client(api_key=apikey)
model_name = "gemini-flash-latest"
CHATS_DIR = Path("chats")
console = Console()
USER_LABEL = Style(color="cyan", bold=True)
AI_LABEL = Style(color="green", bold=True)


def prompt_user() -> str:
    console.print()
    console.print("User: ", style=USER_LABEL, end="")
    return input().strip()


def print_user(text: str) -> None:
    console.print()
    console.print("User: ", style=USER_LABEL, end="")
    console.print(text, style="cyan")


def print_ai(text: str) -> None:
    console.print()
    console.print("AI: ", style=AI_LABEL, end="")
    console.print(Markdown(text))


def slugify(title: str, max_len: int = 40) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:max_len].strip("-") or "chat"


def extract_title(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if match := re.match(r"^#{1,3}\s+(.+)$", line):
            return match.group(1).strip()
    first = text.strip().splitlines()[0] if text.strip() else ""
    if 0 < len(first) <= 60:
        return first
    return None


def new_chat_path() -> Path:
    CHATS_DIR.mkdir(exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:6]
    return CHATS_DIR / f"{date}-{short_id}.md"


def is_auto_name(path: Path) -> bool:
    return bool(re.fullmatch(r"\d{8}-[a-f0-9]{6}", path.stem))


def maybe_rename_with_title(path: Path, ai_text: str) -> Path:
    if not is_auto_name(path):
        return path
    title = extract_title(ai_text)
    if not title:
        return path
    date = path.stem.split("-", 1)[0]
    new_path = path.with_name(f"{date}-{slugify(title)}.md")
    if new_path != path and not new_path.exists():
        path.rename(new_path)
        return new_path
    return path


def list_chat_files() -> list[Path]:
    if not CHATS_DIR.exists():
        return []
    files = [p for p in CHATS_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def list_chats() -> None:
    files = list_chat_files()
    if not files:
        print(f"No hay chats guardados en '{CHATS_DIR}/'.")
        return
    print(f"Chats guardados ({CHATS_DIR}/):\n")
    for i, path in enumerate(files, 1):
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {i:>3}. {path.name}  ({mtime})")


def parse_chat_file(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :].lstrip("\n")

    turns: list[tuple[str, str]] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_lines
        if current_role and current_lines:
            content = "\n".join(current_lines).strip()
            if current_role == "user":
                turns.append((content, ""))
            elif turns and not turns[-1][1]:
                user, _ = turns.pop()
                turns.append((user, content))
        current_role = None
        current_lines = []

    for line in text.splitlines():
        if line.startswith("User: "):
            flush()
            current_role = "user"
            current_lines = [line[6:]]
        elif line.startswith("AI: "):
            flush()
            current_role = "ai"
            current_lines = [line[4:]]
        elif current_role:
            current_lines.append(line)
        elif line.strip():
            flush()

    flush()
    return [(u, a) for u, a in turns if u and a]


def build_history(pairs: list[tuple[str, str]]) -> list[dict]:
    history = []
    for user_text, ai_text in pairs:
        history.append({"role": "user", "parts": [{"text": user_text}]})
        history.append({"role": "model", "parts": [{"text": ai_text}]})
    return history


def append_turn(path: Path, user_input: str, ai_text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(f"User: {user_input}\nAI: {ai_text}\n\n")


def display_history(pairs: list[tuple[str, str]]) -> None:
    for user_text, ai_text in pairs:
        print_user(user_text)
        print_ai(ai_text)


def get_models(output=None):
    try:
        results = [f"{m.name}:{m.supported_actions}" for m in client.models.list()]
        content = "\n".join(results)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(content)
    except Exception as e:
        print(f"\n[ERROR API]: {e}")


def simple_query(req, context=None, output=None):
    try:
        config = {"system_instruction": context} if context else None
        res = client.models.generate_content(model=model_name, contents=req, config=config)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(res.text)
        else:
            print_user(req)
            print_ai(res.text)
    except Exception as e:
        print(f"\n[ERROR API]: {e}")


def start_chat(context=None, output_path: Path | None = None, history_pairs: list[tuple[str, str]] | None = None):
    config = {"system_instruction": context} if context else None
    history = build_history(history_pairs) if history_pairs else []
    chat = client.chats.create(model=model_name, config=config, history=history)

    chat_file = output_path or new_chat_path()
    chat_file.parent.mkdir(parents=True, exist_ok=True)
    if history_pairs and not chat_file.exists():
        for user_text, ai_text in history_pairs:
            append_turn(chat_file, user_text, ai_text)

    turns_saved = 0
    if history_pairs:
        print(f"--- Chat reanudado ({chat_file.name}, {len(history_pairs)} turnos) ---")
        display_history(history_pairs)
    else:
        print(f"--- Chat iniciado ({chat_file.name}, escribe 'exit' para salir) ---")

    try:
        while True:
            user_input = prompt_user()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break

            try:
                res = chat.send_message(user_input)
                full_text = res.text
                print_ai(full_text)
                append_turn(chat_file, user_input, full_text)
                turns_saved += 1
                chat_file = maybe_rename_with_title(chat_file, full_text)
            except Exception as e:
                print(f"\n[ERROR API]: {e}")
                print("Puedes intentar escribir de nuevo...")

    except (EOFError, KeyboardInterrupt):
        print("\nChat interrumpido por el usuario.")

    print("\nChat finalizado.", end="")
    if turns_saved:
        print(f" Guardado en: {chat_file}")
    elif history_pairs:
        print(" (sin mensajes nuevos)")
    else:
        print(" (sin mensajes guardados)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Command-line interface for Gemini AI.")
    parser.add_argument("-m", "--models", action="store_true", help="Listar modelos disponibles")
    parser.add_argument("-l", "--list", action="store_true", help="Listar chats guardados")
    parser.add_argument(
        "-n",
        "--continue-chat",
        type=int,
        metavar="N",
        help="Continuar el chat número N (ver --list)",
    )
    parser.add_argument("-c", "--chat", action="store_true", help="Iniciar chat (por defecto sin argumentos)")
    parser.add_argument("-x", "--context", help="Archivo de contexto / system instruction")
    parser.add_argument("-o", "--output", help="Ruta de guardado (por defecto: chats/YYYYMMDD-titulo.md)")
    parser.add_argument("request", nargs="?", help="Consulta única (sin entrar al modo chat)")

    args = parser.parse_args()

    context_text = None
    if args.context:
        try:
            with open(args.context, "r", encoding="utf-8") as f:
                context_text = f.read().strip()
        except Exception as e:
            print(f"Error leyendo el contexto: {e}")
            sys.exit(1)

    output_path = Path(args.output) if args.output else None

    if args.models:
        get_models(args.output)
    elif args.list:
        list_chats()
    elif args.continue_chat is not None:
        files = list_chat_files()
        if not files:
            print(f"No hay chats guardados en '{CHATS_DIR}/'.")
            sys.exit(1)
        if args.continue_chat < 1 or args.continue_chat > len(files):
            print(f"Número inválido. Usa --list para ver chats del 1 al {len(files)}.")
            sys.exit(1)
        chat_path = files[args.continue_chat - 1]
        history_pairs = parse_chat_file(chat_path)
        if not history_pairs:
            print(f"El archivo '{chat_path.name}' no tiene turnos válidos para reanudar.")
            sys.exit(1)
        start_chat(context_text, chat_path, history_pairs)
    elif args.request:
        simple_query(args.request, context_text, args.output)
    else:
        start_chat(context_text, output_path)
