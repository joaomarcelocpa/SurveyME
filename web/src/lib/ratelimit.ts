import { createHash, randomBytes } from "node:crypto";

// Somente em memoria (por instancia): nada disso vai ao banco.
// Freio contra inundacao automatizada, nao contra pessoas: o limite e alto de proposito,
// porque muitos participantes podem dividir a mesma rede (campus, sala de aula).
// A repeticao por pessoa e tratada pelo marcador no aparelho (Survey.tsx) e na analise.
const salt = randomBytes(16).toString("hex");
const hits = new Map<string, number[]>();

export const WINDOW_MS = 10 * 60 * 1000;
export const MAX_HITS = 100;

export function allow(rawKey: string, now = Date.now()): boolean {
  const key = createHash("sha256").update(salt + rawKey).digest("hex");
  const recent = (hits.get(key) ?? []).filter((t) => now - t < WINDOW_MS);
  if (recent.length >= MAX_HITS) {
    hits.set(key, recent);
    return false;
  }
  recent.push(now);
  hits.set(key, recent);
  if (hits.size > 5000) {
    for (const [k, v] of hits) if (v.every((t) => now - t >= WINDOW_MS)) hits.delete(k);
  }
  return true;
}

export function _reset() {
  hits.clear();
}
