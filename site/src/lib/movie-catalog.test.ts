import { describe, expect, it } from "vitest";
import { createCatalogSearch, detailPath, recommendations, type CatalogTitle } from "./movie-catalog";
const title = (i: string, t: string, o?: string): CatalogTitle => ({ i, t, o, a: 1994, p: null, n: 8.7, g: [] });
const catalog = [title("f278", "Um Sonho de Liberdade", "The Shawshank Redemption"), title("f238", "O Poderoso Chefão", "The Godfather"), title("s1396", "Breaking Bad")];
describe("static movie catalog", () => {
  it("finds Portuguese titles regardless of accents, case and punctuation", () => { expect(createCatalogSearch(catalog)("PODEROSO, chefao")[0]?.i).toBe("f238"); });
  it("finds the original title", () => { expect(createCatalogSearch(catalog)("shawshank")[0]?.i).toBe("f278"); });
  it("tolerates typing errors", () => { expect(createCatalogSearch(catalog)("breakng bad")[0]?.i).toBe("s1396"); });
  it("limits autocomplete to eight titles", () => { expect(createCatalogSearch(Array.from({ length: 12 }, (_, i) => title(`f${i}`, "Filme parecido")))("Filme parecido")).toHaveLength(8); });
  it("prefers popularity order for equal matches", () => { expect(createCatalogSearch([title("f2", "Teste"), title("f1", "Teste")])("Teste")[0]?.i).toBe("f2"); });
  it("uses modulo 50 for the two documented shards", () => { expect(detailPath("f278")).toBe("/dados/detalhes/f-28.json"); expect(detailPath("s1396")).toBe("/dados/detalhes/s-46.json"); });
  it("skips missing recommendations and preserves the same type", () => { expect(recommendations("f278", ["f999", "s1396", "f238"], catalog).map(t => t.i)).toEqual(["f238"]); });
});