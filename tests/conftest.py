import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Cada teste usa um SQLite e uma pasta de documentos próprios."""
    monkeypatch.setenv("LEGALFLOW_DADOS", str(tmp_path))
    monkeypatch.delenv("TEAMS_WEBHOOK_PADRAO", raising=False)
    from legalflow import banco

    banco.inicializar()
    yield tmp_path
