"""Restaura respostas de um backup JSONL em um banco (insere; nunca apaga nem altera).

Uso: DATABASE_URL_ADMIN=... python scripts/restore.py ~/survey-backups/responses-XXXX.jsonl --yes
Linhas ja existentes (mesmo id) sao ignoradas; ao final confere que cada resposta do arquivo existe no banco
com conteudo identico. Se houver manifest.json ao lado, confere o hash do arquivo antes de inserir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backup  # noqa: E402


def check_file(path: Path) -> list[str]:
    problemas = []
    manifest = backup.load_manifest(path.parent)
    entrada = next((e for e in manifest if e["arquivo"] == path.name), None)
    if entrada and hashlib.sha256(path.read_bytes()).hexdigest() != entrada["sha256_arquivo"]:
        problemas.append("hash do arquivo difere do manifesto")
    return problemas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--table", default="responses")
    ap.add_argument("--yes", action="store_true", help="confirma a insercao no banco de destino")
    a = ap.parse_args(argv)

    path = Path(a.arquivo).expanduser()
    rows = backup.read_backup(path)
    for p in check_file(path):
        print("ERRO:", p, file=sys.stderr)
        return 1
    print(f"{len(rows)} respostas no arquivo")
    if not a.yes:
        print("simulacao: nada foi inserido (use --yes para inserir)")
        return 0
    url = os.environ.get("DATABASE_URL_ADMIN")
    if not url or a.table not in backup.TABELAS:
        print("defina DATABASE_URL_ADMIN e use uma tabela valida", file=sys.stderr)
        return 2
    import psycopg

    novos = 0
    with psycopg.connect(url, connect_timeout=15) as con, con.cursor() as cur:
        for r in rows:
            c = backup.canon_row(r)
            cur.execute(
                f"insert into {a.table} (id, created_at, form_version, consent, answers) values (%s,%s,%s,%s,%s) on conflict (id) do nothing",
                (c["id"], c["created_at"], c["form_version"], c["consent"], json.dumps(c["answers"])))
            novos += cur.rowcount
        con.commit()
    atual = backup.fetch_rows(url, a.table)
    por_id = {backup.canon_row(r)["id"]: backup.row_hash(r) for r in atual}
    divergentes = [backup.canon_row(r)["id"] for r in rows if por_id.get(backup.canon_row(r)["id"]) != backup.row_hash(r)]
    print(f"inseridas: {novos} | ja existiam: {len(rows) - novos} | banco agora: {len(atual)}")
    if divergentes:
        print(f"ATENCAO: {len(divergentes)} respostas diferem do arquivo: {divergentes[:5]}", file=sys.stderr)
        return 1
    print("conferido: todas as respostas do arquivo existem no banco com conteudo identico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
