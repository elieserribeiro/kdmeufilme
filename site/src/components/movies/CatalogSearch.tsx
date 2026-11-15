import { useId, useMemo, useState } from "react";
import { Search, ArrowUpRight, Loader2, Film } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { createCatalogSearch, type CatalogTitle } from "@/lib/movie-catalog";
export function Poster({ title, small = false }: { title: CatalogTitle; small?: boolean }) {
  const [failed, setFailed] = useState(false);
  return <div className={`movie-poster ${small ? "w-10 shrink-0 rounded" : "w-full rounded-xl"}`}>
    {title.p && !failed ? <img src={`https://image.tmdb.org/t/p/${small ? "w92" : "w342"}${title.p}`} alt={title.t} loading="lazy" onError={() => setFailed(true)} className="h-full w-full object-cover" /> : <div className="flex h-full flex-col items-center justify-center gap-3 p-2 text-muted-foreground"><Film size={small ? 18 : 36} />{!small && <span className="text-center text-sm">{title.t}</span>}</div>}
  </div>;
}
export function CatalogSearch({ catalog, loading, error, retry }: { catalog: CatalogTitle[]; loading: boolean; error: boolean; retry: () => void }) {
  const [query, setQuery] = useState(""); const [open, setOpen] = useState(false); const [active, setActive] = useState(-1);
  const search = useMemo(() => createCatalogSearch(catalog), [catalog]);
  const results = useMemo(() => query.trim() ? search(query) : [], [query, search]);
  const navigate = useNavigate(); const id = useId();
  const choose = (t: CatalogTitle) => { setOpen(false); setQuery(""); setActive(-1); navigate(`/kdmeufilme/titulo/${t.i}`); };
  return <div className="relative w-full text-left">
    <div className="movie-search flex items-center gap-3 rounded-xl border border-hairline bg-card px-4 py-3 sm:px-5">
      {loading ? <Loader2 className="shrink-0 animate-spin text-primary" size={22} /> : <Search className="shrink-0 text-primary" size={22} />}
      <input role="combobox" aria-label="Buscar filme ou série" aria-expanded={open && !!query.trim()} aria-controls={id} aria-autocomplete="list" aria-activedescendant={active >= 0 ? `${id}-${active}` : undefined} disabled={loading || error} value={query} placeholder={loading ? "Carregando catálogo…" : error ? "Catálogo indisponível" : "Qual filme ou série você ama?"} onChange={e => { setQuery(e.target.value); setOpen(true); setActive(-1); }} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={e => {
        if (e.key === "Escape") setOpen(false);
        if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setActive(a => Math.min(a + 1, results.length - 1)); }
        if (e.key === "ArrowUp") { e.preventDefault(); setActive(a => Math.max(a - 1, 0)); }
        if (e.key === "Enter" && results.length) { e.preventDefault(); const t = results[Math.max(0, active)]; if (t) choose(t); }
      }} className="min-w-0 flex-1 bg-transparent text-base text-foreground outline-none placeholder:text-muted-foreground sm:text-lg" />
      <Button variant="ember" size="icon" aria-label="Buscar" disabled={!results.length} onClick={() => { const t = results[Math.max(0, active)]; if (t) choose(t); }} className="h-11 w-11 rounded-lg"><ArrowUpRight /></Button>
    </div>
    {error && <div className="mt-3 text-sm text-muted-foreground">Não foi possível carregar o catálogo. <Button variant="link" onClick={retry}>Tentar novamente</Button></div>}
    {open && query.trim() && <div id={id} role="listbox" className="absolute left-0 right-0 top-full z-40 mt-2 max-h-96 overflow-auto rounded-xl border border-hairline bg-popover p-2 shadow-elevated">
      {!results.length ? <p className="p-4 text-sm text-muted-foreground">Não encontramos esse título. Tente o nome em português ou o original.</p> : results.map((t, i) => <Button key={t.i} id={`${id}-${i}`} role="option" aria-selected={active === i} variant="ghost" onMouseDown={e => e.preventDefault()} onClick={() => choose(t)} className={`h-auto w-full justify-start whitespace-normal px-3 py-2 text-left hover:bg-secondary hover:text-foreground ${active === i ? "bg-secondary text-foreground" : ""}`}><Poster key={t.i} title={t} small /><span className="min-w-0 flex-1"><span className="block font-medium">{t.t}</span>{t.o && <span className="block text-xs text-muted-foreground">{t.o}</span>}<span className="text-xs text-muted-foreground">{t.a || "Ano indisponível"}</span></span><span className="movie-tag">{t.i[0] === "f" ? "Filme" : "Série"}</span></Button>)}
    </div>}
  </div>;
}
