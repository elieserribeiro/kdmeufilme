"""Detecta se dois títulos são da mesma franquia (continuações, spin-offs com o mesmo nome).

Regra, em duas partes:
  1. Os nomes "base" são iguais. O nome base é o título sem o subtítulo (o que vem
     depois de ':' ou ' - ') e sem números de continuação. Ex.: "Toy Story 3" -> "toy story";
     "Batman: O Cavaleiro das Trevas" -> "batman".  Compara título em português e original.
  2. OU o nome base de um aparece dentro do título do outro E os dois têm alguma pessoa
     em comum (diretor/criador ou ator) ou pelo menos 3 palavras-chave em comum.
     Ex.: "Naruto" e "Boruto: Naruto Next Generations"; "The Dark Knight" e "The Dark Knight
     Rises". Exigir algo em comum evita falsos positivos como "Dark" x "Dark Matter".
  3. OU começam com as mesmas duas palavras E têm alguém ou 3 palavras-chave em comum
     ("Harry Potter e a Pedra Filosofal" x "Harry Potter e a Câmara Secreta").
  4. OU compartilham uma palavra-chave de "universo" do TMDB, como
     "marvel cinematic universe (mcu)" ou "dc extended universe (dceu)".
"""
import re
import unicodedata

SUFIXOS_CONTINUACAO = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "part", "parte", "chapter", "capitulo", "vol", "volume", "movie", "filme",
}
PALAVRAS_VAZIAS = {"the", "a", "an", "o", "os", "as", "um", "uma", "de", "do", "da",
                   "la", "el", "le", "les", "los", "der", "die", "das"}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def _palavras(texto):
    return re.findall(r"\w+", texto)


def _base(titulo):
    """'Toy Story 3' -> 'toy story'; 'Batman: O Cavaleiro das Trevas' -> 'batman'."""
    primeira_parte = re.split(r":| - | – | — ", _normalizar(titulo))[0]
    palavras = _palavras(primeira_parte)
    while len(palavras) > 1 and (palavras[-1].isdigit() or palavras[-1] in SUFIXOS_CONTINUACAO):
        palavras.pop()
    base = " ".join(palavras)
    if len(base) < 3 or base in PALAVRAS_VAZIAS:
        return None
    return base


def _inicio(titulo):
    """As duas primeiras palavras 'de verdade': 'Harry Potter e a Pedra...' -> 'harry potter'."""
    palavras = [p for p in _palavras(_normalizar(titulo)) if p not in PALAVRAS_VAZIAS]
    return " ".join(palavras[:2]) if len(palavras) >= 2 else None


# Palavras-chave do TMDB que indicam um "universo" compartilhado (ex.: Marvel)
UNIVERSOS_EXTRAS = {"monsterverse", "arrowverse", "view askewniverse"}


def _universos(palavras_chave):
    return {k for k in palavras_chave
            if k in UNIVERSOS_EXTRAS or re.search(r"universe \([a-z]+\)$", k)}


def preparar(titulo):
    """Calcula uma vez, por título, o que a comparação precisa."""
    nomes = {titulo["title"], titulo["original_title"]}
    return {
        "bases": {b for b in (_base(n) for n in nomes) if b},
        "completos": {" " + " ".join(_palavras(_normalizar(n))) + " " for n in nomes},
        "inicios": {i for i in (_inicio(n) for n in nomes) if i},
        "pessoas": set(titulo["directors"]) | set(titulo["cast"]),
        "universos": _universos(titulo["keywords"]),
        "palavras": set(titulo["keywords"]),
    }


def mesma_franquia(a, b):
    """a e b vêm de preparar()."""
    if a["bases"] & b["bases"]:                       # Toy Story / Toy Story 3
        return True
    if a["universos"] & b["universos"]:               # Vingadores / Pantera Negra (MCU)
        return True
    # Nomes com número que funcionam como marca, ex.: "007: Cassino Royale" x "007 Contra Goldfinger"
    for x, y in ((a, b), (b, a)):
        for base in x["bases"]:
            if re.search(r"\d", base) and any(f" {base} " in c for c in y["completos"]):
                return True
    # Daqui em diante, exige algo em comum: uma pessoa ou pelo menos 3 palavras-chave
    if not (a["pessoas"] & b["pessoas"]) and len(a["palavras"] & b["palavras"]) < 3:
        return False
    if a["inicios"] & b["inicios"]:            # Harry Potter e a... / 007 Contra...
        return True
    for x, y in ((a, b), (b, a)):              # Naruto / Boruto: Naruto Next Generations
        for base in x["bases"]:
            if any(f" {base} " in c for c in y["completos"]):
                return True
    return False
