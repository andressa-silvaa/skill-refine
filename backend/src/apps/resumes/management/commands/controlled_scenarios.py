"""
Os 16 currículos de prova, sem PII — carregados de `controlled_scenarios.json`.

Separado do management command porque é fixture, não lógica: o comando persiste e escreve o índice,
esta lista descreve o que ele persiste. Os cenários cobrem currículo vazio, estagiário, pleno,
sênior, troca de área, autodidata e perfil raso, e são a entrada da validação manual do TCC.

Em JSON e não em literal Python porque é dado: 400 linhas de dicionário aninhado dentro de um `.py`
escondem as ~100 linhas de código que realmente decidem alguma coisa, e nada aqui precisa ser
executado para ser lido.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SCENARIOS_PATH = Path(__file__).resolve().parent / "controlled_scenarios.json"


@lru_cache(maxsize=1)
def _load() -> tuple[tuple[str, dict], ...]:
    rows = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return tuple((str(row["key"]), dict(row["payload"])) for row in rows)


def build_scenarios() -> list[tuple[str, dict]]:
    """Fresh copies, so a caller mutating a payload cannot poison the next call."""
    import copy

    return [(key, copy.deepcopy(payload)) for key, payload in _load()]
