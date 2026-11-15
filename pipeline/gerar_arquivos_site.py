"""Gera os arquivos de dados que o site (Lovable) vai ler.

Entrada:  dados/processados/titulos.json   (gerado por pipeline/preparar_dados.py)
Saída:    site/public/dados/indice.json       -> busca e cartões (carregado uma vez)
          site/public/dados/detalhes/*.json    -> sinopse, elenco e recomendações, em 100 partes
                                                  (f-0 ... f-49, s-0 ... s-49), carregadas só
                                                  quando a pessoa escolhe um título
          Use --saida para gravar em outra pasta (ex.: a pasta public/dados de outro site).

Como o site acha o arquivo de detalhes de um título:
    id "f278"  -> filme, tmdb_id 278  -> 278 % 50 = 28 -> detalhes/f-28.json
    id "s1396" -> série, tmdb_id 1396 -> 1396 % 50 = 46 -> detalhes/s-46.json

Uso:  python pipeline/gerar_arquivos_site.py
      python pipeline/gerar_arquivos_site.py --saida ../meu-site/public/dados
"""
import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recomendador import calcular_todos, carregar_titulos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "site" / "public" / "dados"
PARTES = 50


def arquivo_detalhes(id_titulo):
    return f"{id_titulo[0]}-{int(id_titulo[1:]) % PARTES}.json"


def salvar(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser(description="Gera os arquivos de dados do site")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO,
                        help="pasta de destino (padrão: site/public/dados)")
    SAIDA = parser.parse_args().saida.resolve()

    titulos = carregar_titulos()
    print(f"Calculando recomendações para {len(titulos)} títulos...")
    recomendacoes = calcular_todos(titulos)

    # Apaga só o que este script gera (nunca a pasta de destino inteira)
    if (SAIDA / "detalhes").exists():
        shutil.rmtree(SAIDA / "detalhes")

    # 1) Índice: o mínimo para buscar e desenhar um cartão (pôster, título, ano, nota, gêneros)
    indice = []
    for t in sorted(titulos, key=lambda t: -t["vote_count"]):   # mais conhecidos primeiro
        item = {"i": t["id"], "t": t["title"], "a": t["year"], "p": t["poster_path"],
                "n": t["vote_average"], "g": t["genres"][:3]}
        if t["original_title"] != t["title"]:
            item["o"] = t["original_title"]
        indice.append(item)
    salvar(SAIDA / "indice.json", indice)

    # 2) Detalhes, divididos em partes
    partes = defaultdict(dict)
    for t in titulos:
        partes[arquivo_detalhes(t["id"])][t["id"]] = {
            "sinopse": t["overview"],
            "sinopse_idioma": t["overview_lang"],
            "direcao": t["directors"],
            "elenco": t["cast"][:4],
            "duracao": t["runtime"],
            "temporadas": t["seasons"],
            "votos": t["vote_count"],
            "imdb": t["imdb_id"],
            "tmdb": t["tmdb_id"],
            "recomendacoes": [rid for rid, _ in recomendacoes[t["id"]]],
        }
    for nome, conteudo in partes.items():
        salvar(SAIDA / "detalhes" / nome, conteudo)

    tamanho_indice = (SAIDA / "indice.json").stat().st_size / 1e6
    tamanhos = [p.stat().st_size / 1e3 for p in (SAIDA / "detalhes").iterdir()]
    print(f"indice.json: {len(indice)} títulos, {tamanho_indice:.1f} MB")
    print(f"detalhes/: {len(tamanhos)} arquivos, de {min(tamanhos):.0f} a {max(tamanhos):.0f} KB")
    print(f"Pronto: {SAIDA}")


if __name__ == "__main__":
    main()
