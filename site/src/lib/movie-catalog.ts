import Fuse from "fuse.js";

export type CatalogTitle = { i: string; t: string; o?: string; a: number | null; p: string | null; n: number | null; g: string[] };
export type TitleDetails = { sinopse: string; sinopse_idioma: string; direcao: string[]; elenco: string[]; duracao: number | null; temporadas: number | null; votos: number; imdb: string; tmdb: number; recomendacoes: string[] };
export const normalizeTitle = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
export function createCatalogSearch(titles: CatalogTitle[]) {
  const items = titles.map((title, rank) => ({ title, rank, t: normalizeTitle(title.t), o: normalizeTitle(title.o || "") }));
  const fuse = new Fuse(items, { keys: ["t", "o"], threshold: 0.38, ignoreLocation: true, includeScore: true });
  return (query: string) => fuse.search(normalizeTitle(query)).sort((a, b) => (a.score || 0) - (b.score || 0) || a.item.rank - b.item.rank).slice(0, 8).map(r => r.item.title);
}
export function detailPath(id: string) {
  if (!/^[fs]\d+$/.test(id)) return null;
  return `/dados/detalhes/${id[0]}-${Number(id.slice(1)) % 50}.json`;
}
export function recommendations(id: string, ids: string[], catalog: CatalogTitle[]) {
  const lookup = new Map(catalog.map(t => [t.i, t]));
  return [...new Set(ids)].filter(i => i !== id && i[0] === id[0]).flatMap(i => { const t = lookup.get(i); return t ? [t] : []; });
}
let indexPromise: Promise<CatalogTitle[]> | undefined;
const shards = new Map<string, Promise<Record<string, TitleDetails>>>();
export function loadCatalog() {
  if (!indexPromise) indexPromise = fetch("/dados/indice.json").then(r => { if (!r.ok) throw new Error("catalog"); return r.json(); }).catch(e => { indexPromise = undefined; throw e; });
  return indexPromise;
}
export async function loadDetails(id: string): Promise<TitleDetails | null> {
  const path = detailPath(id);
  if (!path) return null;
  let pending = shards.get(path);
  if (!pending) {
    pending = fetch(path).then(async r => { if (!r.ok || !r.headers.get("content-type")?.includes("json")) return {}; return r.json(); }).catch(() => { shards.delete(path); return {}; });
    shards.set(path, pending);
  }
  return (await pending)[id] || null;
}