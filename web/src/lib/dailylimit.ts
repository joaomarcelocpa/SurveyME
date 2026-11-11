// Contador diario por origem, com TTL, fora do banco de respostas (Upstash Redis via REST).
// A chave e um hash irreversivel (HMAC com segredo) e expira sozinha em 24h. Falha aberta:
// se o servico estiver indisponivel, nao bloqueia participantes legitimos.
import { createHmac } from "node:crypto";

export const DAILY_MAX = 3;
export const DAILY_TTL_S = 86_400;

type Fetch = typeof fetch;

export function makeDailyLimit(url: string, token: string, salt: string, fetchImpl: Fetch = fetch) {
  return async function allowToday(rawKey: string): Promise<boolean> {
    const key = "rl:" + createHmac("sha256", salt).update(rawKey).digest("hex");
    try {
      const res = await fetchImpl(`${url}/pipeline`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify([["INCR", key], ["EXPIRE", key, DAILY_TTL_S, "NX"]]),
        cache: "no-store",
      });
      if (!res.ok) return true;
      const data = (await res.json()) as { result?: number }[];
      const count = Number(data?.[0]?.result);
      return Number.isFinite(count) ? count <= DAILY_MAX : true;
    } catch {
      return true;
    }
  };
}
