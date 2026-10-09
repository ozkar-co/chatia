import argparse
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

import deepseek
import paths
import ui

USER_MARK = "User: "
AI_MARK = "AI: "


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


def new_chat_path(title: str | None) -> Path:
    paths.CHATS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    stem = f"{date}-{slugify(title)}" if title else f"{date}-{uuid.uuid4().hex[:6]}"
    path = paths.CHATS_DIR / f"{stem}.md"
    counter = 2
    while path.exists():
        path = paths.CHATS_DIR / f"{stem}-{counter}.md"
        counter += 1
    return path


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
    if not paths.CHATS_DIR.exists():
        return []
    files = [p for p in paths.CHATS_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def list_chats() -> None:
    files = list_chat_files()
    if not files:
        print(f"No hay chats guardados en '{paths.CHATS_DIR}'.")
        return
    print(f"Chats guardados ({paths.CHATS_DIR}):\n")
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
        if line.startswith(USER_MARK):
            flush()
            current_role = "user"
            current_lines = [line[len(USER_MARK) :]]
        elif line.startswith(AI_MARK):
            flush()
            current_role = "ai"
            current_lines = [line[len(AI_MARK) :]]
        elif current_role:
            current_lines.append(line)
        elif line.strip():
            flush()

    flush()
    return [(u, a) for u, a in turns if u and a]


def build_messages(context: str | None, pairs: list[tuple[str, str]]) -> list[dict]:
    messages: list[dict] = []
    if context:
        messages.append({"role": "system", "content": context})
    for user_text, ai_text in pairs:
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": ai_text})
    return messages


def append_turn(path: Path, user_input: str, ai_text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{USER_MARK}{user_input}\n{AI_MARK}{ai_text}\n\n")


def start_chat(
    api_key: str,
    model: str,
    context: str | None,
    chat_file: Path,
    history_pairs: list[tuple[str, str]] | None = None,
) -> None:
    history_pairs = history_pairs or []
    messages = build_messages(context, history_pairs)

    chat_file.parent.mkdir(parents=True, exist_ok=True)
    if history_pairs and not chat_file.exists():
        for user_text, ai_text in history_pairs:
            append_turn(chat_file, user_text, ai_text)

    turns_saved = 0
    if history_pairs:
        print(ui.info(f"--- Chat reanudado ({chat_file.name}, {len(history_pairs)} turnos) ---"))
        for user_text, ai_text in history_pairs:
            ui.print_user(user_text)
            ui.print_ai(ai_text)
    else:
        print(ui.info(f"--- Chat iniciado ({chat_file.name}, escribe 'exit' para salir) ---"))

    try:
        while True:
            user_input = ui.prompt_user()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            messages.append({"role": "user", "content": user_input})
            try:
                full_text = ui.print_ai_stream(deepseek.stream(api_key, model, messages))
            except deepseek.DeepSeekError as error:
                print(ui.error(f"\n[ERROR API] {error}"))
                messages.pop()
                print("Puedes intentar escribir de nuevo...")
                continue

            messages.append({"role": "assistant", "content": full_text})
            append_turn(chat_file, user_input, full_text)
            turns_saved += 1
            chat_file = maybe_rename_with_title(chat_file, full_text)

    except (EOFError, KeyboardInterrupt):
        print("\nChat interrumpido por el usuario.")

    print("\nChat finalizado.", end="")
    if turns_saved:
        print(f" Guardado en: {chat_file}")
    elif history_pairs:
        print(" (sin mensajes nuevos)")
    else:
        print(" (sin mensajes guardados)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="chatia", description="Chat de terminal con DeepSeek.")
    parser.add_argument(
        "-m",
        "--model",
        choices=sorted(deepseek.MODELS),
        default="flash",
        help="Modelo a usar: flash (por defecto) o pro",
    )
    parser.add_argument("-l", "--list", action="store_true", help="Listar chats guardados")
    parser.add_argument(
        "-n",
        "--continue-chat",
        type=int,
        metavar="N",
        help="Continuar el chat número N (ver --list)",
    )
    parser.add_argument("-x", "--context", metavar="ARCHIVO", help="Archivo de contexto (system instruction)")
    parser.add_argument("-o", "--output", metavar="TITULO", help="Título del chat (opcional)")
    args = parser.parse_args()

    if args.list:
        list_chats()
        return

    context_text = None
    if args.context:
        context_path = Path(args.context)
        if not context_path.is_file():
            print(ui.error(f"Error: no existe el archivo de contexto '{args.context}'"), file=sys.stderr)
            sys.exit(1)
        context_text = context_path.read_text(encoding="utf-8").strip()

    api_key = paths.load_api_key()
    model = deepseek.MODELS[args.model]

    if args.continue_chat is not None:
        files = list_chat_files()
        if not files:
            print(ui.error(f"No hay chats guardados en '{paths.CHATS_DIR}'."), file=sys.stderr)
            sys.exit(1)
        if args.continue_chat < 1 or args.continue_chat > len(files):
            print(
                ui.error(f"Número inválido. Usa --list para ver chats del 1 al {len(files)}."),
                file=sys.stderr,
            )
            sys.exit(1)
        chat_path = files[args.continue_chat - 1]
        history_pairs = parse_chat_file(chat_path)
        if not history_pairs:
            print(
                ui.error(f"El archivo '{chat_path.name}' no tiene turnos válidos para reanudar."),
                file=sys.stderr,
            )
            sys.exit(1)
        start_chat(api_key, model, context_text, chat_path, history_pairs)
    else:
        start_chat(api_key, model, context_text, new_chat_path(args.output))


if __name__ == "__main__":
    main()
