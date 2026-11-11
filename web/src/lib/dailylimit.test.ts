import { describe, expect, it, vi } from "vitest";
import { DAILY_MAX, makeDailyLimit } from "./dailylimit";

const reply = (n: number) => ({ ok: true, json: async () => [{ result: n }, { result: 1 }] }) as unknown as Response;

describe("makeDailyLimit", () => {
  it("permite ate o maximo e bloqueia depois", async () => {
    const f = vi.fn();
    const allow = makeDailyLimit("https://r.test", "tok", "salt", f as never);
    f.mockResolvedValueOnce(reply(DAILY_MAX));
    expect(await allow("1.2.3.4")).toBe(true);
    f.mockResolvedValueOnce(reply(DAILY_MAX + 1));
    expect(await allow("1.2.3.4")).toBe(false);
  });

  it("nunca envia o IP em claro e usa TTL", async () => {
    const f = vi.fn().mockResolvedValue(reply(1));
    await makeDailyLimit("https://r.test", "tok", "salt", f as never)("1.2.3.4");
    const body = f.mock.calls[0][1].body as string;
    expect(body).not.toContain("1.2.3.4");
    expect(body).toContain("EXPIRE");
  });

  it("falha aberta se o servico cair", async () => {
    const f = vi.fn().mockRejectedValue(new Error("rede"));
    expect(await makeDailyLimit("https://r.test", "tok", "salt", f as never)("x")).toBe(true);
  });
});
