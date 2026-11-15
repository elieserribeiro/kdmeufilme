"""Coleta filmes e séries populares do TMDB, em português (pt-BR).

Não precisa instalar nada além do Python: usa só bibliotecas que já vêm com ele.

Antes de rodar:
  1. Crie um arquivo chamado .env na pasta principal do projeto com a linha:
         TMDB_TOKEN=cole_aqui_o_seu_API_Read_Access_Token
  2. O .env NUNCA deve ir para o GitHub (o .gitignore já o exclui).

Uso (a partir da pasta principal do projeto):
  python pipeline/coletar_tmdb.py --teste    -> coleta rápida (~40 títulos) para conferir
  python pipeline/coletar_tmdb.py            -> coleta completa (leva uns 15–30 minutos)

Se a coleta for interrompida, basta rodar de novo: ela continua de onde parou.

Saída: dados/brutos/tmdb_filmes.jsonl e dados/brutos/tmdb_series.jsonl
       (um título por linha, em formato JSON)

Este produto usa a API do TMDB, mas não é endossado nem certificado pelo TMDB.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SAIDA = RAIZ / "dados" / "brutos"
API = "https://api.themoviedb.org/3"
IDIOMA = "pt-BR"

# Quantidade de títulos (o TMDB permite no máximo 500 páginas de 20 = 10.000 por lista)
PAGINAS = {"MOVIE": 500, "SHOW": 300}           # ~10.000 filmes e ~6.000 séries
VOTOS_MINIMOS = {"MOVIE": 100, "SHOW": 50}      # ignora títulos quase desconhecidos
MAX_ATORES, MAX_DIRETORES, MAX_PALAVRAS = 5, 2, 20
TRABALHADORES = 8                               # requisições em paralelo

ARQUIVOS = {"MOVIE": "tmdb_filmes.jsonl", "SHOW": "tmdb_series.jsonl"}
ROTAS = {"MOVIE": "movie", "SHOW": "tv"}


# ---------------------------------------------------------------- token e API
def ler_token():
    token = os.environ.get("TMDB_TOKEN")
    arquivo_env = RAIZ / ".env"
    if not token and arquivo_env.exists():
        for linha in arquivo_env.read_text(encoding="utf-8-sig").splitlines():
            if linha.strip().startswith("TMDB_TOKEN="):
                token = linha.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        sys.exit("ERRO: token não encontrado. Crie o arquivo .env na pasta principal "
                 "do projeto com a linha TMDB_TOKEN=seu_token")
    return token


class ClienteTMDB:
    def __init__(self, token):
        self.cabecalhos = {"Authorization": f"Bearer {token}", "accept": "application/json"}

    def get(self, caminho, **parametros):
        url = f"{API}{caminho}?{urllib.parse.urlencode(parametros)}"
        for tentativa in range(6):
            try:
                req = urllib.request.Request(url, headers=self.cabecalhos)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as erro:
                if erro.code == 401:
                    sys.exit("ERRO 401: o token foi recusado. Confira se você copiou o "
                             "'API Read Access Token' (o longo, que começa com eyJ).")
                if erro.code == 404:
                    return None
                if erro.code == 429:  # muitas requisições: espera e tenta de novo
                    time.sleep(float(erro.headers.get("Retry-After", 2)) + tentativa)
                    continue
                if erro.code >= 500:
                    time.sleep(2 ** tentativa)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(2 ** tentativa)
        return None


# ---------------------------------------------------------- extrair os campos
def _ano(data):
    return int(data[:4]) if data and data[:4].isdigit() else None


def _sinopse_em(traducoes, idioma, pais=None):
    for t in (traducoes or {}).get("translations", []):
        if t.get("iso_639_1") == idioma and (pais is None or t.get("iso_3166_1") == pais):
            texto = (t.get("data") or {}).get("overview")
            if texto:
                return texto
    return ""


def extrair(d, tipo):
    """Guarda só os campos úteis da resposta de detalhes do TMDB."""
    filme = tipo == "MOVIE"
    creditos = d.get("credits") or {}
    elenco = sorted(creditos.get("cast", []), key=lambda p: p.get("order", 999))
    palavras = d.get("keywords") or {}
    palavras = palavras.get("keywords") or palavras.get("results") or []

    if filme:
        diretores = [p["name"] for p in creditos.get("crew", []) if p.get("job") == "Director"]
        paises = [p["iso_3166_1"] for p in d.get("production_countries", [])]
    else:
        diretores = [p["name"] for p in d.get("created_by", [])]   # criadores da série
        paises = d.get("origin_country") or [p["iso_3166_1"] for p in d.get("production_countries", [])]

    duracao = d.get("runtime") if filme else (d.get("episode_run_time") or [None])[0]
    imdb_id = d.get("imdb_id") if filme else (d.get("external_ids") or {}).get("imdb_id")
    sinopse_pt = d.get("overview") or _sinopse_em(d.get("translations"), "pt")

    return {
        "tmdb_id": d["id"],
        "type": tipo,
        "title": d.get("title") if filme else d.get("name"),
        "original_title": d.get("original_title") if filme else d.get("original_name"),
        "original_language": d.get("original_language"),
        "release_year": _ano(d.get("release_date") if filme else d.get("first_air_date")),
        "overview_pt": sinopse_pt,
        "overview_en": _sinopse_em(d.get("translations"), "en", "US")
                       or _sinopse_em(d.get("translations"), "en"),
        "genres": [g["name"] for g in d.get("genres", [])],
        "countries": paises,
        "directors": list(dict.fromkeys(diretores))[:MAX_DIRETORES],
        "cast": [p["name"] for p in elenco[:MAX_ATORES]],
        "keywords": [k["name"] for k in palavras[:MAX_PALAVRAS]],
        "runtime": duracao,
        "seasons": None if filme else d.get("number_of_seasons"),
        "poster_path": d.get("poster_path"),
        "vote_average": d.get("vote_average"),
        "vote_count": d.get("vote_count"),
        "popularity": d.get("popularity"),
        "imdb_id": imdb_id,
    }


# ----------------------------------------------------------------- a coleta
def listar_ids(cliente, tipo, paginas):
    """Lista os ids dos títulos com mais votos (os mais conhecidos)."""
    ids, rota = [], ROTAS[tipo]
    for pagina in range(1, paginas + 1):
        resp = cliente.get(f"/discover/{rota}", language=IDIOMA, page=pagina,
                           sort_by="vote_count.desc", include_adult="false",
                           **{"vote_count.gte": VOTOS_MINIMOS[tipo]})
        if not resp or not resp.get("results"):
            break
        ids.extend(r["id"] for r in resp["results"])
        if pagina >= resp.get("total_pages", 0):
            break
        if pagina % 50 == 0:
            print(f"   listados {len(ids)} ids...")
    return list(dict.fromkeys(ids))


def coletar(cliente, tipo, paginas):
    nome = "filmes" if tipo == "MOVIE" else "séries"
    arquivo = PASTA_SAIDA / ARQUIVOS[tipo]
    ja_coletados = set()
    if arquivo.exists():
        with arquivo.open(encoding="utf-8") as f:
            ja_coletados = {json.loads(l)["tmdb_id"] for l in f if l.strip()}

    print(f"\n[{nome}] listando os mais populares...")
    ids = listar_ids(cliente, tipo, paginas)
    faltam = [i for i in ids if i not in ja_coletados]
    print(f"[{nome}] {len(ids)} encontrados, {len(ja_coletados)} já coletados, "
          f"{len(faltam)} a coletar")

    extras = "credits,keywords,translations" + ("" if tipo == "MOVIE" else ",external_ids")
    trava, feitos, inicio = threading.Lock(), 0, time.time()

    def baixar(tmdb_id):
        d = cliente.get(f"/{ROTAS[tipo]}/{tmdb_id}", language=IDIOMA,
                        append_to_response=extras)
        return extrair(d, tipo) if d else None

    with arquivo.open("a", encoding="utf-8") as saida, \
            ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
        for futuro in as_completed([pool.submit(baixar, i) for i in faltam]):
            registro = futuro.result()
            with trava:
                if registro:
                    saida.write(json.dumps(registro, ensure_ascii=False) + "\n")
                feitos += 1
                if feitos % 250 == 0 or feitos == len(faltam):
                    saida.flush()
                    taxa = feitos / max(time.time() - inicio, 1)
                    restante = (len(faltam) - feitos) / max(taxa, 0.1) / 60
                    print(f"   {feitos}/{len(faltam)}  (~{restante:.0f} min restantes)")
    print(f"[{nome}] pronto: {arquivo}")


def main():
    parser = argparse.ArgumentParser(description="Coleta filmes e séries do TMDB")
    parser.add_argument("--teste", action="store_true",
                        help="coleta só 1 página de cada tipo (~40 títulos)")
    args = parser.parse_args()

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    if args.teste:
        global ARQUIVOS
        ARQUIVOS = {k: v.replace(".jsonl", "_teste.jsonl") for k, v in ARQUIVOS.items()}

    cliente = ClienteTMDB(ler_token())
    for tipo in ("MOVIE", "SHOW"):
        coletar(cliente, tipo, 1 if args.teste else PAGINAS[tipo])
    print("\nColeta concluída.")


if __name__ == "__main__":
    main()
