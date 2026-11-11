import { beforeEach, describe, expect, it, vi } from "vitest";
import { _reset } from "./ratelimit";
import { processSubmission } from "./submit";

const base = {
  Q1: "sim", Q2: "sim", Q3: "5-8", Q4: "nao", Q5: "1-2", Q6: "semanal", Q7: ["chatgpt"],
  Q8: "varia", Q9: "duvidas", Q10: 3, Q11: 3, Q12: 3, Q13: 3, Q14: 3, Q15: 3, Q16: 3, Q17: 3, Q18: 1,
};
const good = () => ({ consent: true, website: "", duration_s: 200, answers: { ...base } });

let insert: ReturnType<typeof vi.fn>;
const deps = (o = {}) => ({ open: true, clientKey: "k", insert: insert as never, ...o });

beforeEach(() => {
  _reset();
  insert = vi.fn().mockResolvedValue(undefined);
});

describe("processSubmission", () => {
  it("grava resposta valida com duration_s dentro de answers", async () => {
    expect(await processSubmission(good(), deps())).toEqual({ ok: true });
    expect(insert).toHaveBeenCalledOnce();
    expect(insert.mock.calls[0][1]).toMatchObject({ Q1: "sim", duration_s: 200 });
  });

  it("recusa quando SURVEY_OPEN esta fechado", async () => {
    const r = await processSubmission(good(), deps({ open: false }));
    expect(r.ok).toBe(false);
    expect(insert).not.toHaveBeenCalled();
  });

  it("honeypot preenchido finge sucesso e nao grava", async () => {
    const r = await processSubmission({ ...good(), website: "x" }, deps());
    expect(r.ok).toBe(true);
    expect(insert).not.toHaveBeenCalled();
  });

  it("recusa sem consentimento, opcao invalida e chave extra", async () => {
    for (const bad of [
      { ...good(), consent: false },
      { ...good(), answers: { ...base, Q6: "nunca" } },
      { ...good(), answers: { ...base, email: "a@b.c" } },
      { ...good(), answers: { ...base, Q10: 7 } },
    ]) {
      expect((await processSubmission(bad, deps())).ok).toBe(false);
    }
    expect(insert).not.toHaveBeenCalled();
  });

  it("recusa fora da populacao-alvo", async () => {
    const r = await processSubmission({ ...good(), answers: { ...base, Q1: "nao" } }, deps());
    expect(r.ok).toBe(false);
  });

  it("aceita falha na atencao (descarte e feito na analise)", async () => {
    const r = await processSubmission({ ...good(), answers: { ...base, Q18: 4 } }, deps());
    expect(r.ok).toBe(true);
  });

  it("recusa quando o limite diario estourou", async () => {
    const r = await processSubmission(good(), deps({ dailyLimit: async () => false }));
    expect(r.ok).toBe(false);
    expect(insert).not.toHaveBeenCalled();
  });

  it("aplica rate limit", async () => {
    for (let i = 0; i < 5; i++) await processSubmission(good(), deps());
    expect((await processSubmission(good(), deps())).ok).toBe(false);
  });
});
