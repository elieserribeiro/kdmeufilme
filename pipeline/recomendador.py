"""Recomendador por conteúdo (dados do TMDB).

Compara cada título só com outros do MESMO TIPO (filme com filme, série com série),
somando cinco "sinais" de semelhança, cada um com um peso:

  - sinopse         palavras da sinopse (em inglês, que está completa em quase todos)
  - palavras-chave  temas do TMDB, ex.: "prison", "time travel", "heist"
  - gêneros         gêneros raros (Animação, Terror, Faroeste) pesam mais que comuns (Drama)
  - pessoas         diretores/criadores e atores principais em comum
  - origem          país de produção e idioma original

Depois soma um bônus de qualidade (nota e nº de votos), para preferir títulos bem avaliados.
Calcula em blocos, para não estourar a memória com ~10 mil títulos.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import franquias  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TITULOS = RAIZ / "dados" / "processados" / "titulos.json"

PESOS = {"sinopse": 0.30, "palavras": 0.25, "generos": 0.25, "pessoas": 0.12, "origem": 0.08}
PESO_QUALIDADE = 0.20     # quanto a qualidade influencia a ordem final (0 = nada)
VIZINHOS = 10             # quantos recomendados guardar por título (o site mostra 3)
CANDIDATOS = 60           # quantos avaliar antes de tirar os da mesma franquia
BLOCO = 1000


def carregar_titulos():
    with TITULOS.open(encoding="utf-8") as f:
        return json.load(f)


def _tfidf_listas(listas):
    """TF-IDF em que cada item da lista (um gênero, uma palavra-chave, uma pessoa) é um 'termo'."""
    vec = TfidfVectorizer(analyzer=lambda x: x, min_df=1)
    return vec.fit_transform(listas).astype(np.float32)


def matrizes(grupo):
    """Uma matriz por sinal; cada linha é um título, normalizada (similaridade = produto)."""
    sinopse = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.5,
                              ngram_range=(1, 2), sublinear_tf=True)
    return {
        "sinopse": sinopse.fit_transform([t["overview_compare"] for t in grupo]).astype(np.float32),
        "palavras": _tfidf_listas([t["keywords"] for t in grupo]),
        "generos": _tfidf_listas([t["genres_compare"] for t in grupo]),
        "pessoas": _tfidf_listas([t["directors"] + t["cast"] for t in grupo]),
        "origem": _tfidf_listas([t["countries"] + [f"idioma:{t['original_language']}"]
                                 for t in grupo]),
    }


def qualidade(grupo):
    """Nota de 0 a 1: 60% nota média + 40% popularidade (nº de votos em escala log)."""
    nota = np.array([(t["vote_average"] or 5.0) / 10 for t in grupo], dtype=np.float32)
    votos = np.log1p(np.array([t["vote_count"] for t in grupo], dtype=np.float32))
    return 0.6 * nota + 0.4 * votos / votos.max()


def vizinhos(grupo, n=VIZINHOS):
    """Para cada título, devolve (índices dos n mais recomendados, semelhança de cada um)."""
    mats = matrizes(grupo)
    bonus = qualidade(grupo)[None, :]
    total = len(grupo)
    indices = np.zeros((total, n), dtype=np.int32)
    semelhancas = np.zeros((total, n), dtype=np.float32)

    for ini in range(0, total, BLOCO):
        fim = min(ini + BLOCO, total)
        sim = np.zeros((fim - ini, total), dtype=np.float32)
        for nome, m in mats.items():
            sim += PESOS[nome] * (m[ini:fim] @ m.T).toarray()
        sim[np.arange(fim - ini), np.arange(ini, fim)] = -1      # nunca o próprio título
        pontos = (1 - PESO_QUALIDADE) * sim + PESO_QUALIDADE * bonus
        pontos[np.arange(fim - ini), np.arange(ini, fim)] = -np.inf
        top = np.argpartition(-pontos, n, axis=1)[:, :n]
        ordem = np.take_along_axis(pontos, top, axis=1).argsort(axis=1)[:, ::-1]
        top = np.take_along_axis(top, ordem, axis=1)
        indices[ini:fim] = top
        semelhancas[ini:fim] = np.take_along_axis(sim, top, axis=1)
    return indices, semelhancas


def calcular_todos(titulos, n=VIZINHOS):
    """Recomendações de todos os títulos: {id: [(id_recomendado, semelhança), ...]}.

    Regra de franquias: nunca recomenda um título da mesma franquia do escolhido,
    e no máximo um título de cada franquia na lista (ex.: não traz O Poderoso Chefão 1 e 2).
    """
    resultado = {}
    for tipo in ("MOVIE", "SHOW"):
        grupo = [t for t in titulos if t["type"] == tipo]
        info = [franquias.preparar(t) for t in grupo]
        idx, sim = vizinhos(grupo, CANDIDATOS)
        for i, t in enumerate(grupo):
            escolhidos = []
            for j, s in zip(idx[i], sim[i]):
                if franquias.mesma_franquia(info[i], info[j]):
                    continue
                if any(franquias.mesma_franquia(info[k], info[j]) for k, _ in escolhidos):
                    continue
                escolhidos.append((j, float(s)))
                if len(escolhidos) == n:
                    break
            resultado[t["id"]] = [(grupo[j]["id"], s) for j, s in escolhidos]
    return resultado
