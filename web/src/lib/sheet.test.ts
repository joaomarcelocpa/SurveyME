import { describe, expect, it, vi } from "vitest";
import { HEADERS, buildRow, mirrorToSheet } from "./sheet";
import { itemsInOrder } from "./questionnaire";

const answers = {
  Q1: "sim", Q2: "sim", Q3: "5-8", Q4: "nao", Q5: "1-2", Q6: "semanal", Q7: ["chatgpt", "claude"],
  Q8: "varia", Q9: ["duvidas", "gerar_testes"], Q10: 3, Q11: 3, Q12: 3, Q13: 3, Q14: 3, Q15: 3, Q16: 3, Q17: 3,
  Q18: 1, Q19: "ajudou_pouco", Q20: "=IMPORTXML(\"x\")", duration_s: 210,
};
const input = { id: "abc", createdAt: "2026-11-13T12:00:00.000Z", answers };

describe("planilha (copia secundaria)", () => {
  it("cabecalho e linha tem o mesmo tamanho, na ordem das telas", () => {
    expect(buildRow(input)).toHaveLength(HEADERS.length);
    expect(HEADERS[0]).toBe("Carimbo de data/hora");
    expect(HEADERS[1]).toMatch(/^Q1\. /);
    expect(HEADERS.at(-1)).toBe("ID da resposta");
  });

  it("converte opcoes em rotulos, multipla em lista e mantem numeros", () => {
    const row = buildRow(input);
    const col = (id: string) => row[1 + itemsInOrder.findIndex((i) => i.id === id)];
    expect(col("Q9")).toBe("Tirar dúvidas e pedir explicações, Gerar testes automatizados");
    expect(col("Q10")).toBe(3);
    expect(col("Q3")).not.toBe("5-8");
    expect(row.at(-2)).toBe(210);
    expect(row.at(-1)).toBe("abc");
  });

  it("neutraliza formula em texto livre e deixa vazio o que nao foi respondido", () => {
    const { Q20, ...semAberta } = answers;
    expect(buildRow(input)[1 + itemsInOrder.findIndex((i) => i.id === "Q20")]).toBe("'=IMPORTXML(\"x\")");
    expect(buildRow({ ...input, answers: semAberta })[1 + itemsInOrder.findIndex((i) => i.id === "Q20")]).toBe("");
  });

  it("envia token, cabecalho e linha; sucesso so quando o receptor responde ok", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    expect(await mirrorToSheet(input, { url: "https://x", secret: "s", fetchImpl: f as never })).toBe(true);
    const sent = JSON.parse(f.mock.calls[0][1].body);
    expect(sent.token).toBe("s");
    expect(sent.headers).toEqual(HEADERS);
    expect(sent.row).toHaveLength(HEADERS.length);
  });

  it("nunca lanca: rede caindo, HTTP de erro ou receptor recusando devolvem false", async () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => {});
    for (const f of [
      vi.fn().mockRejectedValue(new Error("rede")),
      vi.fn().mockResolvedValue(new Response("x", { status: 500 })),
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: false }), { status: 200 })),
    ]) {
      expect(await mirrorToSheet(input, { url: "https://x", secret: "s", fetchImpl: f as never })).toBe(false);
    }
    expect(JSON.stringify(quiet.mock.calls)).not.toContain("ajudou");
    quiet.mockRestore();
  });
});
