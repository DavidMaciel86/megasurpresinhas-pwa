# core.py
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import List, Optional, Tuple

import requests

# API alternativa (formato compatível com a lógica inicial)
# Ex.: https://api.guidi.dev.br/loteria/megasena/ultimo  :contentReference[oaicite:1]{index=1}
API_ALT_BASE = "https://api.guidi.dev.br/loteria/megasena"
API_ALT_ULTIMO = f"{API_ALT_BASE}/ultimo"

COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
}

# Cache: por padrão vai para ~/.local/share/MegaSurpresinhas/cache_megasena.json
# Sobrescrever com env var MEGASURP_CACHE_PATH (útil no Render)
DEFAULT_CACHE_PATH = (
    Path(os.getenv("MEGASURP_CACHE_PATH", ""))
    if os.getenv("MEGASURP_CACHE_PATH")
    else Path.home() / ".local" / "share" / "MegaSurpresinhas" / "cache_megasena.json"
)


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


def coletar_ultimos_10_resultados_alt() -> List[int]:
    ultimo_concurso = obter_ultimo_concurso_alt()
    pool: List[int] = []

    for concurso in range(ultimo_concurso, ultimo_concurso - 10, -1):
        dados = obter_concurso_alt(concurso)

        # Blindagem leve
        lista_dezenas = dados.get("listaDezenas") or []
        if not lista_dezenas:
            continue

        dezenas_int = [int(d) for d in lista_dezenas]
        pool.extend(dezenas_int)

    if not pool:
        raise RuntimeError("Não foi possível coletar dezenas na API alternativa.")
    return pool


def preparar_pool_com_globo() -> List[int]:
    """
    Mantida para compatibilidade: retorna SOMENTE o pool.
    (Sem status para não quebrar o código atual.)
    """
    pool, _modo, _fonte, _mensagem = preparar_pool_com_globo_com_status()
    return pool


def preparar_pool_com_globo_com_status() -> Tuple[List[int], str, str, str]:
    """
    Retorna: (pool, modo, fonte, mensagem)

    modo:  "online" | "cache" | "offline"
    fonte: "api_alt" | "cache" | "estatistico"
    """
    # 1) tenta online (API alternativa)
    try:
        pool = coletar_ultimos_10_resultados_alt()
        pool.extend(range(1, 61))  # chance mínima p/ todas as dezenas

        # salva cache (último concurso + pool bruto dos últimos 10)
        _salvar_cache(
            {
                "fonte": "api_alt",
                "ultimo_concurso": obter_ultimo_concurso_alt(),
                "pool_ultimos_10": pool[:-60],  # só as dezenas vindas dos 10 concursos
            }
        )

        return (
            pool,
            "online",
            "api_alt",
            "Dados atualizados via consulta à internet. Cache foi atualizado.",
        )

    except requests.exceptions.RequestException:
        # 2) tenta cache
        cache = _ler_cache()
        if cache and cache.get("pool_ultimos_10"):
            pool_cache = [int(x) for x in cache["pool_ultimos_10"]]
            pool_cache.extend(range(1, 61))
            return (
                pool_cache,
                "cache",
                "cache",
                "Não foi possível atualizar agora. Usando dados salvos localmente (cache).",
            )

        # 3) offline / estatístico
        pool_offline = list(range(1, 61))
        return (
            pool_offline,
            "offline",
            "estatistico",
            "Modo offline/Usando gerador estatístico: sem acesso à internet (API) e sem cache disponível.",
        )

    except Exception:
        # Mesma lógica: tenta cache, senão offline
        cache = _ler_cache()
        if cache and cache.get("pool_ultimos_10"):
            pool_cache = [int(x) for x in cache["pool_ultimos_10"]]
            pool_cache.extend(range(1, 61))
            return (
                pool_cache,
                "cache",
                "cache",
                "Falha ao processar atualização. Usando dados salvos localmente (cache).",
            )

        pool_offline = list(range(1, 61))
        return (
            pool_offline,
            "offline",
            "estatistico",
            "Modo offline/Usando gerador estatístico: falha geral e sem cache disponível.",
        )


def gerar_surpresinhas(
    qtd_surpresinhas: int,
    qtd_dezenas: int,
    pool_dezenas: List[int],
) -> List[List[int]]:
    surpresinhas: List[List[int]] = []

    if not pool_dezenas:
        raise ValueError("Pool de dezenas vazio.")

    for _ in range(qtd_surpresinhas):
        jogo: List[int] = []
        # Evita loop infinito em pools ruins
        tentativas = 0
        while len(jogo) < qtd_dezenas:
            tentativas += 1
            if tentativas > 10_000:
                raise RuntimeError("Não foi possível montar um jogo com o pool atual.")
            numero = random.choice(pool_dezenas)
            if numero not in jogo:
                jogo.append(numero)

        jogo.sort()
        surpresinhas.append(jogo)

    return surpresinhas
