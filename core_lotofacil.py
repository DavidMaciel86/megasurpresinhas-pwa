from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import List, Optional, Tuple

import requests

# =====================================================
# API alternativa – Lotofácil
# =====================================================

API_ALT_BASE = "https://api.guidi.dev.br/loteria/lotofacil"
API_ALT_ULTIMO = f"{API_ALT_BASE}/ultimo"

COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
}

# Cache local (mesma ideia da Mega-Sena)
DEFAULT_CACHE_PATH = (
    Path(os.getenv("LOTOFACIL_CACHE_PATH", ""))
    if os.getenv("LOTOFACIL_CACHE_PATH")
    else Path.home()
    / ".local"
    / "share"
    / "MegaSurpresinhas"
    / "cache_lotofacil.json"
)


# =====================================================
# Cache helpers
# =====================================================

def _cache_path() -> Path:
    path = DEFAULT_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _salvar_cache(payload: dict) -> None:
    path = _cache_path()
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _ler_cache() -> Optional[dict]:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# =====================================================
# API – coleta de resultados
# =====================================================

def obter_ultimo_concurso_alt() -> int:
    resp = requests.get(API_ALT_ULTIMO, headers=COMMON_HEADERS, timeout=15)
    resp.raise_for_status()
    dados = resp.json()
    return int(dados["numero"])


def obter_concurso_alt(numero_concurso: int) -> dict:
    url = f"{API_ALT_BASE}/{numero_concurso}"
    resp = requests.get(url, headers=COMMON_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def coletar_ultimos_3_resultados_alt() -> List[int]:
    ultimo = obter_ultimo_concurso_alt()
    pool: List[int] = []

    for concurso in range(ultimo, ultimo - 3, -1):
        dados = obter_concurso_alt(concurso)
        dezenas = dados.get("listaDezenas") or []
        if dezenas:
            pool.extend(int(d) for d in dezenas)

    if not pool:
        raise RuntimeError("Não foi possível coletar dados da Lotofácil.")
    return pool


# =====================================================
# Pool com status (online / cache / offline)
# =====================================================

def preparar_pool_lotofacil_com_status() -> Tuple[List[int], str, str, str]:
    """
    Retorna:
      pool, modo, fonte, mensagem

    modo:  online | cache | offline
    fonte: api_alt | cache | estatistico
    """

    # 1️⃣ Online (API alternativa)
    try:
        pool = coletar_ultimos_3_resultados_alt()
        pool.extend(range(1, 26))

        _salvar_cache(
            {
                "fonte": "api_alt",
                "ultimo_concurso": obter_ultimo_concurso_alt(),
                "pool_ultimos_3": pool[:-25],
            }
        )

        return (
            pool,
            "online",
            "api_alt",
            "Dados atualizados via internet. Cache da Lotofácil atualizado.",
        )

    except requests.exceptions.RequestException:
        pass
    except Exception:
        pass

    # 2️⃣ Cache local
    cache = _ler_cache()
    if cache and cache.get("pool_ultimos_3"):
        pool_cache = [int(x) for x in cache["pool_ultimos_3"]]
        pool_cache.extend(range(1, 26))

        return (
            pool_cache,
            "cache",
            "cache",
            "Sem conexão. Usando dados salvos localmente (cache da Lotofácil).",
        )

    # 3️⃣ Offline / estatístico
    return (
        list(range(1, 26)),
        "offline",
        "estatistico",
        "Modo offline: gerador estatístico (1–25).",
    )


def preparar_pool_lotofacil() -> List[int]:
    """
    Versão simples (compatibilidade).
    Retorna apenas o pool.
    """
    pool, _, _, _ = preparar_pool_lotofacil_com_status()
    return pool


# =====================================================
# Geração de surpresinhas
# =====================================================

def gerar_surpresinhas_lotofacil(
    qtd_jogos: int,
    qtd_dezenas: int,
    pool: List[int],
) -> List[List[int]]:

    if not (15 <= qtd_dezenas <= 20):
        raise ValueError("Lotofácil: quantidade de dezenas deve ser entre 15 e 20.")

    jogos: List[List[int]] = []

    for _ in range(qtd_jogos):
        jogo: List[int] = []

        while len(jogo) < qtd_dezenas:
            n = random.choice(pool)
            if n not in jogo:
                jogo.append(n)

        jogo.sort()
        jogos.append(jogo)

    return jogos
