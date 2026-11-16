"""Carrega variaveis de arquivos .env (KEY=VALOR) sem sobrescrever as ja definidas no ambiente."""
from __future__ import annotations

import os
from pathlib import Path


def parse(texto: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        if linha.startswith("export "):
            linha = linha[7:].lstrip()
        chave, _, valor = linha.partition("=")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "'\"":
            valor = valor[1:-1]
        elif " #" in valor:
            valor = valor.split(" #", 1)[0].rstrip()
        if chave.strip():
            out[chave.strip()] = valor
    return out


def load_env(*caminhos: Path | str) -> list[str]:
    """Le os arquivos na ordem dada; o primeiro que define uma variavel vence, e o ambiente real vence todos."""
    carregados = []
    for c in caminhos:
        p = Path(c).expanduser()
        if p.is_file():
            for k, v in parse(p.read_text(encoding="utf-8")).items():
                os.environ.setdefault(k, v)
            carregados.append(str(p))
    return carregados
