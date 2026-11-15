"""Limpa e prepara os filmes e séries coletados do TMDB.

Entrada:  dados/brutos/tmdb_filmes.jsonl e dados/brutos/tmdb_series.jsonl
          (gerados por pipeline/coletar_tmdb.py)
Saída:    dados/processados/titulos.json

Uso:  python pipeline/preparar_dados.py   (rodar a partir da pasta principal do projeto)
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos"
PROCESSADOS = RAIZ / "dados" / "processados"

# Gêneros de séries que o TMDB não traduz -> nome em português para exibir
GENEROS_SERIES = {
    "Action & Adventure": "Ação e Aventura",
    "Sci-Fi & Fantasy": "Ficção científica e Fantasia",
    "War & Politics": "Guerra e Política",
    "Kids": "Infantil",
    "Soap": "Novela",
    "Reality": "Reality show",
    "Talk": "Talk show",
    "News": "Jornalismo",
}
# Para COMPARAR filmes com séries de forma coerente, os gêneros combinados são separados
GENEROS_PARA_COMPARAR = {
    "Ação e Aventura": ["Ação", "Aventura"],
    "Ficção científica e Fantasia": ["Ficção científica", "Fantasia"],
    "Guerra e Política": ["Guerra", "Política"],
}

# Palavras-chave que descrevem só o "tom" ou detalhes técnicos: atrapalham a comparação
PALAVRAS_RUIDO = {
    "aftercreditsstinger", "duringcreditsstinger", "woman director", "affectation", "cliché",
    "amused", "hilarious", "dramatic", "suspenseful", "admiring", "inspirational", "aggressive",
    "nostalgic", "romantic", "playful", "cheerful", "adoring", "excited", "witty", "mysterious",
    "shocking", "philosophical", "audacious", "lighthearted", "comforting", "whimsical",
    "enthusiastic", "ambiguous", "joyful", "melancholy", "thoughtful", "hopeful", "anxious",
    "angry", "campy", "vibrant", "cautionary", "appreciative", "disturbed", "sentimental",
    "loving", "depressing", "antagonistic", "assertive", "satirical", "reflective", "empathetic",
    "provocative", "tragic", "curious", "baffled", "surreal", "complicated", "exhilarated",
    "melodramatic", "ambivalent", "cynical", "critical", "defiant", "frantic", "introspective",
    "mischievous", "biting", "informative", "powerful", "irreverent", "celebratory",
    "sympathetic", "ridiculous", "joyous", "bewildered", "questioning", "exuberant", "horrified",
    "farcical", "distressing", "dreary", "frightened", "casual", "enchant", "serious", "zealous",
    "sarcastic", "frustrated", "disheartening", "meditative", "speculative", "haunting",
    "disgusted", "ominous", "arrogant", "pretentious", "understated", "unassuming", "wistful",
    "approving", "gritty", "foreboding", "optimistic", "embarrassed", "euphoric", "gloomy",
    "apathetic", "relaxed", "inspiring", "exciting", "doubtful", "dubious", "callous",
    "malicious", "intense", "absurd", "bold", "incredulous", "prophetic", "intellectual",
    "high concept", "epic", "tense", "sincere", "harsh", "kind", "hopeless", "urgent",
    "vindictive", "absurdist", "familiar", "dignified", "condescending", "skeptical",
}


def ler_jsonl(caminho):
    with caminho.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def limpar(t):
    # Gêneros: tradução dos gêneros de séries + versão "separada" para comparar
    generos = [GENEROS_SERIES.get(g, g) for g in t.get("genres") or []]
    comparar = []
    for g in generos:
        comparar.extend(GENEROS_PARA_COMPARAR.get(g, [g]))

    palavras = [k.strip().lower() for k in t.get("keywords") or []]
    palavras = [k for k in palavras if k and k not in PALAVRAS_RUIDO]

    sinopse_pt = (t.get("overview_pt") or "").strip()
    sinopse_en = (t.get("overview_en") or "").strip()
    titulo = (t.get("title") or t.get("original_title") or "").strip()
    original = (t.get("original_title") or titulo).strip()
    ano = int(t["release_year"]) if t.get("release_year") else None

    return {
        "id": f"{'f' if t['type'] == 'MOVIE' else 's'}{t['tmdb_id']}",   # f155, s1396
        "tmdb_id": t["tmdb_id"],
        "type": t["type"],
        "title": titulo,
        "original_title": original,
        "year": ano,
        # para exibir: português; se faltar, inglês (marcado para o site avisar)
        "overview": sinopse_pt or sinopse_en,
        "overview_lang": "pt" if sinopse_pt else ("en" if sinopse_en else None),
        # para comparar: inglês (presente em quase todos, deixa a comparação uniforme)
        "overview_compare": sinopse_en or sinopse_pt,
        "genres": generos,
        "genres_compare": list(dict.fromkeys(comparar)),
        "countries": t.get("countries") or [],
        "original_language": t.get("original_language"),
        "directors": t.get("directors") or [],
        "cast": t.get("cast") or [],
        "keywords": palavras,
        "runtime": t.get("runtime") if t["type"] == "MOVIE" else None,
        "seasons": t.get("seasons") if t["type"] == "SHOW" else None,
        "poster_path": t.get("poster_path"),
        "vote_average": round(t["vote_average"], 1) if t.get("vote_average") else None,
        "vote_count": t.get("vote_count") or 0,
        "popularity": t.get("popularity"),
        "imdb_id": t.get("imdb_id"),
    }


def main():
    brutos = ler_jsonl(BRUTOS / "tmdb_filmes.jsonl") + ler_jsonl(BRUTOS / "tmdb_series.jsonl")
    print(f"Lidos: {len(brutos)} títulos")

    vistos, titulos = set(), []
    for t in brutos:
        chave = (t["type"], t["tmdb_id"])
        if chave in vistos:
            continue
        vistos.add(chave)
        limpo = limpar(t)
        # sem título ou sem nenhum conteúdo para comparar -> fora
        if not limpo["title"] or not (limpo["overview_compare"] or limpo["keywords"]):
            continue
        titulos.append(limpo)

    filmes = sum(t["type"] == "MOVIE" for t in titulos)
    print(f"Prontos: {len(titulos)} títulos ({filmes} filmes, {len(titulos) - filmes} séries)")
    PROCESSADOS.mkdir(parents=True, exist_ok=True)
    with (PROCESSADOS / "titulos.json").open("w", encoding="utf-8") as f:
        json.dump(titulos, f, ensure_ascii=False)
    print(f"Salvo em {PROCESSADOS / 'titulos.json'}")


if __name__ == "__main__":
    main()
