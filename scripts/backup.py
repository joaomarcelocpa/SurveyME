"""Backup e verificacao das respostas (somente leitura no banco).

Uso (com o usuario survey_ro):
  DATABASE_URL_RO=... python scripts/backup.py            # verifica contra o ultimo backup e salva um novo
  DATABASE_URL_RO=... python scripts/backup.py --verify-only
Saida: arquivos JSONL + manifest.json em SURVEY_BACKUP_DIR (padrao ~/survey-backups), fora do repositorio.
Copia opcional para SURVEY_BACKUP_MIRROR (pasta do grupo). Codigo de saida: 0 ok, 1 divergencia, 2 falha de copia.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

TABELAS = {"responses", "responses_dev"}


# ---------------------------------------------------------------- formato canonico

def _iso(v) -> str:
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    return v.astimezone(timezone.utc).isoformat()


def canon_row(r: dict) -> dict:
    a = r["answers"] if isinstance(r["answers"], dict) else json.loads(r["answers"])
    return {"id": str(r["id"]), "created_at": _iso(r["created_at"]), "form_version": r["form_version"],
            "consent": bool(r["consent"]), "answers": a}


def canon_json(r: dict) -> str:
    return json.dumps(canon_row(r), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def row_hash(r: dict) -> str:
    return hashlib.sha256(canon_json(r).encode("utf-8")).hexdigest()


def state_hash(rows: list[dict]) -> str:
    h = hashlib.sha256()
    for line in sorted(f"{canon_row(r)['id']}:{row_hash(r)}" for r in rows):
        h.update(line.encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------- banco

def fetch_rows(url: str, table: str = "responses") -> list[dict]:
    if table not in TABELAS:
        raise ValueError("tabela nao permitida")
    import psycopg

    with psycopg.connect(url, connect_timeout=15) as con, con.cursor() as cur:
        cur.execute(f"select id, created_at, form_version, consent, answers from {table} order by created_at, id")
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------------------------------------------------------------- arquivos

def backup_dir(arg: str | None = None) -> Path:
    d = Path(arg or os.environ.get("SURVEY_BACKUP_DIR") or Path.home() / "survey-backups").expanduser()
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


def load_manifest(d: Path) -> list[dict]:
    p = d / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _save_manifest(d: Path, m: list[dict]) -> None:
    tmp = d / "manifest.json.tmp"
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, d / "manifest.json")


def read_backup(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def write_backup(rows: list[dict], d: Path, now: datetime | None = None) -> dict | None:
    """Grava um novo backup. Devolve a entrada do manifesto, ou None se nada mudou desde o ultimo."""
    manifest = load_manifest(d)
    estado = state_hash(rows)
    if manifest and manifest[-1]["estado_hash"] == estado:
        return None
    now = now or datetime.now(timezone.utc)
    nome = f"responses-{now.strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    conteudo = "".join(canon_json(r) + "\n" for r in rows)
    caminho = d / nome
    caminho.write_text(conteudo, encoding="utf-8")
    caminho.chmod(0o600)
    entrada = {"arquivo": nome, "gerado_em": now.isoformat(), "total": len(rows),
               "max_created_at": max((canon_row(r)["created_at"] for r in rows), default=None),
               "sha256_arquivo": hashlib.sha256(conteudo.encode("utf-8")).hexdigest(), "estado_hash": estado}
    manifest.append(entrada)
    _save_manifest(d, manifest)
    return entrada


def mirror(d: Path, destino: Path, entrada: dict) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copy2(d / entrada["arquivo"], destino / entrada["arquivo"])
    shutil.copy2(d / "manifest.json", destino / "manifest.json")


# ---------------------------------------------------------------- verificacao

def verify(rows: list[dict], d: Path) -> dict:
    """Compara o banco com o ultimo backup: respostas que sumiram ou mudaram sao problemas."""
    manifest = load_manifest(d)
    if not manifest:
        return {"ok": True, "tem_backup": False, "anterior": 0, "atual": len(rows), "novas": len(rows), "ausentes": [], "alteradas": []}
    ultimo = manifest[-1]
    arquivo = d / ultimo["arquivo"]
    prob_arquivo = None
    if not arquivo.exists():
        prob_arquivo = "arquivo do ultimo backup nao encontrado"
        antes = {}
    else:
        if hashlib.sha256(arquivo.read_bytes()).hexdigest() != ultimo["sha256_arquivo"]:
            prob_arquivo = "arquivo do ultimo backup foi alterado (hash diferente do manifesto)"
        antes = {canon_row(r)["id"]: row_hash(r) for r in read_backup(arquivo)}
    agora = {canon_row(r)["id"]: row_hash(r) for r in rows}
    ausentes = sorted(set(antes) - set(agora))
    alteradas = sorted(i for i in antes if i in agora and antes[i] != agora[i])
    novas = len(set(agora) - set(antes))
    return {"ok": not ausentes and not alteradas and prob_arquivo is None, "tem_backup": True, "anterior": len(antes),
            "atual": len(rows), "novas": novas, "ausentes": ausentes, "alteradas": alteradas,
            "ultimo_backup": ultimo["gerado_em"], "problema_arquivo": prob_arquivo}


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="pasta de backup (padrao: SURVEY_BACKUP_DIR ou ~/survey-backups)")
    ap.add_argument("--mirror", help="pasta de copia (padrao: SURVEY_BACKUP_MIRROR)")
    ap.add_argument("--table", default=os.environ.get("SURVEY_TABLE", "responses"))
    ap.add_argument("--verify-only", action="store_true", help="so verifica, sem gravar backup novo")
    a = ap.parse_args(argv)

    url = os.environ.get("DATABASE_URL_RO")
    if not url:
        print("DATABASE_URL_RO nao definida", file=sys.stderr)
        return 2
    d = backup_dir(a.out)
    try:
        rows = fetch_rows(url, a.table)
    except Exception as e:  # noqa: BLE001
        print(f"FALHA ao ler o banco: {type(e).__name__}", file=sys.stderr)
        return 2

    v = verify(rows, d)
    print(f"banco: {v['atual']} respostas | ultimo backup: {v['anterior']} | novas desde entao: {v['novas']}")
    codigo = 0
    if not v["ok"]:
        codigo = 1
        print("DIVERGENCIA DETECTADA:", file=sys.stderr)
        if v["ausentes"]:
            print(f"  {len(v['ausentes'])} resposta(s) do backup nao existem mais no banco: {v['ausentes'][:5]}", file=sys.stderr)
        if v["alteradas"]:
            print(f"  {len(v['alteradas'])} resposta(s) com conteudo diferente do backup: {v['alteradas'][:5]}", file=sys.stderr)
        if v.get("problema_arquivo"):
            print(f"  {v['problema_arquivo']}", file=sys.stderr)
    if a.verify_only:
        return codigo

    entrada = write_backup(rows, d)
    if entrada is None:
        print("sem mudancas desde o ultimo backup; nada gravado")
        return codigo
    print(f"backup gravado: {d / entrada['arquivo']} ({entrada['total']} respostas)")
    destino = a.mirror or os.environ.get("SURVEY_BACKUP_MIRROR")
    if destino:
        try:
            mirror(d, Path(destino).expanduser(), entrada)
            print(f"copia em: {destino}")
        except OSError as e:
            print(f"FALHA na copia para {destino}: {type(e).__name__}", file=sys.stderr)
            codigo = codigo or 2
    return codigo


if __name__ == "__main__":
    sys.exit(main())
