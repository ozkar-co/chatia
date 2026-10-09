import functools
import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def color(text: str, *codes: str) -> str:
    if not color_enabled():
        return text
    return f"{''.join(codes)}{text}{RESET}"


def styled(*codes: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return color(func(*args, **kwargs), *codes)

        return wrapper

    return decorator


@styled(GREEN, BOLD)
def ai_label() -> str:
    return "AI: "


@styled(CYAN, BOLD)
def user_label() -> str:
    return "User: "


@styled(DIM)
def info(text: str) -> str:
    return text


@styled(RED, BOLD)
def error(text: str) -> str:
    return text


def prompt_user() -> str:
    print()
    print(user_label(), end="", flush=True)
    return input().strip()


def print_user(text: str) -> None:
    print()
    print(user_label(), end="")
    print(color(text, CYAN))


def print_ai(text: str) -> None:
    print()
    print(ai_label(), end="")
    print(text)


def print_ai_stream(chunks) -> str:
    print()
    print(ai_label(), end="", flush=True)
    parts: list[str] = []
    for chunk in chunks:
        parts.append(chunk)
        sys.stdout.write(chunk)
        sys.stdout.flush()
    sys.stdout.write("\n")
    return "".join(parts)
