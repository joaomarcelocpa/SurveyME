import { describe, expect, it, vi } from "vitest";
import { Pool } from "pg";
import { getPool, insertResponse } from "./db";

const row = { id: "11111111-1111-1111-1111-111111111111", created_at: new Date("2026-11-13T12:00:00Z") };

describe("insertResponse", () => {
  it("envia versao e respostas como parametros e devolve id e data", async () => {
    const q = vi.fn().mockResolvedValue({ rows: [row] });
    expect(await insertResponse({ query: q }, "1.0.0", { Q1: "sim", duration_s: 90 })).toEqual(row);
    expect(q.mock.calls[0][1]).toEqual(["1.0.0", JSON.stringify({ Q1: "sim", duration_s: 90 })]);
    expect(q.mock.calls[0][0]).toContain("$2::jsonb");
  });

  it("tenta de novo em falha passageira e para no limite", async () => {
    const q = vi.fn().mockRejectedValueOnce(new Error("timeout")).mockRejectedValueOnce(new Error("reset")).mockResolvedValue({ rows: [row] });
    expect(await insertResponse({ query: q }, "v", {}, { delayMs: 1 })).toEqual(row);
    expect(q).toHaveBeenCalledTimes(3);

    const bad = vi.fn().mockRejectedValue(new Error("fora do ar"));
    await expect(insertResponse({ query: bad }, "v", {}, { delayMs: 1 })).rejects.toThrow("fora do ar");
    expect(bad).toHaveBeenCalledTimes(3);
  });
});

// Teste real, opcional: TEST_DATABASE_URL=postgres://... com a tabela responses ja migrada.
describe.skipIf(!process.env.TEST_DATABASE_URL)("insertResponse com Postgres real", () => {
  it("grava no banco e le de volta", async () => {
    const pool: Pool = getPool(process.env.TEST_DATABASE_URL);
    const saved = await insertResponse(pool, "teste-db", { Q9: ["duvidas", "gerar_testes"], Q10: 3, duration_s: 120 });
    const r = await pool.query("select form_version, consent, answers from responses where id = $1", [saved.id]);
    expect(r.rows[0].form_version).toBe("teste-db");
    expect(r.rows[0].consent).toBe(true);
    expect(r.rows[0].answers.Q9).toEqual(["duvidas", "gerar_testes"]);
    expect(typeof r.rows[0].answers.Q10).toBe("number");
    await pool.end();
  });
});
