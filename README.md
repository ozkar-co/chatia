# chatia

Chat de terminal con la API de DeepSeek. Sin dependencias en runtime
(solo la stdlib de Python).

## Uso

```sh
make setup
make run
make run ARGS="-m pro -o mi-chat"
```

Opciones:

| Flag | Descripción |
|------|-------------|
| `-m, --model` | `flash` (por defecto) o `pro` |
| `-l, --list` | Lista los chats guardados |
| `-n N, --continue-chat N` | Continúa el chat número N |
| `-x, --context ARCHIVO` | Archivo de contexto (system instruction) |
| `-o, --output TITULO` | Título del chat (opcional) |

Siempre se entra en modo chat. `exit` o `quit` para salir. `Ctrl-D`
o `Ctrl-C` también termina.

La API key se lee de `~/docs/key.txt`. Los chats se guardan en
`~/docs/chats/`.

## Deploy

```sh
make dist
```

Empaqueta con Nuitka `--mode=standalone` (onedir) en `dist/main.dist/`.
Se eligió Nuitka porque el programa no tiene dependencias externas:
compila poco código puro y no necesita wheels de terceros.

## Estructura

```
main.py       # CLI y bucle de chat
deepseek.py   # cliente HTTP (urllib) y streaming SSE
ui.py         # color ANSI propio
paths.py      # rutas (~/docs) y carga de la key
```
