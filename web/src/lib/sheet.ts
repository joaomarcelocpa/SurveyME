import { itemsInOrder, type Item } from "./questionnaire";

// Copia secundaria das respostas para uma planilha do Google, no formato de uma planilha do Google Forms:
// uma linha por resposta, uma coluna por pergunta, "Carimbo de data/hora" na primeira coluna.
// O banco (Neon) continua sendo a fonte oficial; falha aqui nunca impede nem desfaz o envio.

export const HEADERS: string[] = [
  "Carimbo de data/hora",
  ...itemsInOrder.map((i) => `${i.id}. ${i.text}`),
  "Duração (s)",
  "ID da resposta",
];

// Texto livre que comece com = + - @ viraria formula na planilha; o apostrofo o mantem como texto.
const literal = (s: string) => (/^[=+\-@]/.test(s) ? `'${s}` : s);

function cell(item: Item, v: unknown): string | number {
  if (v === undefined || v === null) return "";
  const label = (x: unknown) => item.options?.find((o) => o.value === x)?.label ?? String(x);
  switch (item.type) {
    case "likert":
      return typeof v === "number" ? v : literal(String(v));
    case "single":
      return literal(label(v));
    case "multi":
      return literal(Array.isArray(v) ? v.map(label).join(", ") : label(v));
    case "open":
      return literal(String(v));
  }
}

export type MirrorInput = { id: string; createdAt: string; answers: Record<string, unknown> };

export function buildRow({ id, createdAt, answers }: MirrorInput): (string | number)[] {
  const dur = answers.duration_s;
  return [
    createdAt,
    ...itemsInOrder.map((it) => cell(it, answers[it.id])),
    typeof dur === "number" ? dur : "",
    id,
  ];
}

export type MirrorOptions = { url: string; secret: string; fetchImpl?: typeof fetch; timeoutMs?: number };

/** Envia a linha ao receptor (Apps Script). Nunca lanca: devolve false em qualquer falha. */
export async function mirrorToSheet(input: MirrorInput, opts: MirrorOptions): Promise<boolean> {
  const f = opts.fetchImpl ?? fetch;
  try {
    const res = await f(opts.url, {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify({ token: opts.secret, headers: HEADERS, row: buildRow(input) }),
      redirect: "follow",
      signal: AbortSignal.timeout(opts.timeoutMs ?? 10_000),
    });
    const body = (await res.json().catch(() => null)) as { ok?: boolean } | null;
    if (!res.ok || !body?.ok) {
      console.error("sheet_mirror_failed", res.status); // sem conteudo de resposta nem segredo
      return false;
    }
    return true;
  } catch (e) {
    console.error("sheet_mirror_failed", e instanceof Error ? e.name : "erro");
    return false;
  }
}
