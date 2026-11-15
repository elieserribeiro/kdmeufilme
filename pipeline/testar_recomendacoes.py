"""Mostra as 3 recomendações para alguns títulos conhecidos.

Uso:  python pipeline/testar_recomendacoes.py
      python pipeline/testar_recomendacoes.py "Clube da Luta" "Friends"
"""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recomendador import calcular_todos, carregar_titulos  # noqa: E402

TESTES = [
    "Um Sonho de Liberdade", "Interestelar", "Toy Story: Um Mundo de Aventuras", "Klaus",
    "Batman: O Cavaleiro das Trevas", "Titanic", "Corra!", "Cidade de Deus", "Parasita",
    "A Viagem de Chihiro",
    "Breaking Bad", "Stranger Things", "Dark", "Round 6", "The Crown", "Friends",
    "Naruto", "La casa de papel", "Os Simpsons",
]


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c)).strip()


def encontrar(titulos, nome):
    alvo = normalizar(nome)
    achados = [t for t in titulos
               if alvo in (normalizar(t["title"]), normalizar(t["original_title"]))]
    return max(achados, key=lambda t: t["vote_count"]) if achados else None


if __name__ == "__main__":
    titulos = carregar_titulos()
    por_id = {t["id"]: t for t in titulos}
    recs = calcular_todos(titulos)
    for nome in sys.argv[1:] or TESTES:
        t = encontrar(titulos, nome)
        if not t:
            print(f"\n{nome}: não encontrado")
            continue
        tipo = "Filme" if t["type"] == "MOVIE" else "Série"
        print(f"\n{t['title']} ({t['year']}) [{tipo}] — {', '.join(t['genres'])}")
        for rid, sim in recs[t["id"]][:3]:
            r = por_id[rid]
            print(f"   -> {r['title'] + ' (' + str(r['year']) + ')':<50}"
                  f"{', '.join(r['genres'][:3]):<40} nota {r['vote_average']}  sem.={sim:.2f}")
