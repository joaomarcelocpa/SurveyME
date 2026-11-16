import json
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import backup  # noqa: E402
import restore  # noqa: E402
import seed_dev  # noqa: E402


def rows(n=5):
    return seed_dev.gerar(n)


def test_hash_estavel_independe_da_ordem_das_chaves_e_do_fuso():
    r = rows(1)[0]
    r2 = dict(r)
    r2["answers"] = dict(reversed(list(r["answers"].items())))
    r2["created_at"] = r["created_at"].astimezone(timezone(timedelta(hours=-3)))
    assert backup.row_hash(r) == backup.row_hash(r2)


def test_grava_backup_com_manifesto_e_permissao_restrita(tmp_path):
    e = backup.write_backup(rows(), tmp_path)
    assert e["total"] == 5
    arq = tmp_path / e["arquivo"]
    assert stat.S_IMODE(arq.stat().st_mode) == 0o600
    assert len(backup.read_backup(arq)) == 5
    assert backup.load_manifest(tmp_path)[-1]["estado_hash"] == e["estado_hash"]


def test_nao_grava_de_novo_sem_mudancas(tmp_path):
    rs = rows()
    assert backup.write_backup(rs, tmp_path) is not None
    assert backup.write_backup(rs, tmp_path, datetime.now(timezone.utc) + timedelta(hours=1)) is None
    assert len(backup.load_manifest(tmp_path)) == 1


def test_verify_ok_e_novas_respostas(tmp_path):
    rs = rows(6)
    backup.write_backup(rs[:4], tmp_path)
    v = backup.verify(rs, tmp_path)
    assert v["ok"] and v["novas"] == 2 and v["anterior"] == 4


def test_verify_detecta_resposta_removida(tmp_path):
    rs = rows(5)
    backup.write_backup(rs, tmp_path)
    v = backup.verify(rs[:-1], tmp_path)
    assert not v["ok"] and len(v["ausentes"]) == 1


def test_verify_detecta_resposta_alterada(tmp_path):
    rs = rows(5)
    backup.write_backup(rs, tmp_path)
    rs[2]["answers"] = {**rs[2]["answers"], "Q10": 1 if rs[2]["answers"]["Q10"] != 1 else 2}
    v = backup.verify(rs, tmp_path)
    assert not v["ok"] and len(v["alteradas"]) == 1


def test_verify_detecta_arquivo_de_backup_adulterado(tmp_path):
    rs = rows(3)
    e = backup.write_backup(rs, tmp_path)
    p = tmp_path / e["arquivo"]
    p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert not backup.verify(rs, tmp_path)["ok"]


def test_tabela_invalida_e_recusada():
    with pytest.raises(ValueError):
        backup.fetch_rows("postgresql://x", "users")


def test_restore_simulacao_nao_insere_e_confere_hash(tmp_path, capsys):
    e = backup.write_backup(rows(3), tmp_path)
    assert restore.main([str(tmp_path / e["arquivo"])]) == 0
    assert "simulacao" in capsys.readouterr().out
    (tmp_path / e["arquivo"]).write_text("{}\n", encoding="utf-8")
    assert restore.main([str(tmp_path / e["arquivo"])]) == 1


def test_dois_backups_no_mesmo_instante_nao_se_sobrescrevem(tmp_path):
    instante = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
    a = backup.write_backup(rows(3), tmp_path, instante)
    b = backup.write_backup(rows(4), tmp_path, instante)
    assert a["arquivo"] != b["arquivo"]
    assert len(backup.read_backup(tmp_path / a["arquivo"])) == 3
    assert len(backup.read_backup(tmp_path / b["arquivo"])) == 4
    assert restore.check_file(tmp_path / a["arquivo"]) == []


def test_envfile_le_valores_sem_sobrescrever_o_ambiente(tmp_path, monkeypatch):
    import envfile
    f = tmp_path / ".env"
    f.write_text("# c\nA=1\nexport B='x y'\nC=\"z\"\nD=v # nota\nINVALIDA\nPRESA=do_arquivo\n", encoding="utf-8")
    assert envfile.parse(f.read_text(encoding="utf-8")) == {"A": "1", "B": "x y", "C": "z", "D": "v", "PRESA": "do_arquivo"}
    monkeypatch.setenv("PRESA", "do_ambiente")
    monkeypatch.delenv("A", raising=False)
    envfile.load_env(f, tmp_path / "nao-existe")
    import os
    assert os.environ["A"] == "1" and os.environ["PRESA"] == "do_ambiente"
