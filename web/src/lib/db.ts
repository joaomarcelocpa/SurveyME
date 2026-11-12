import { Pool } from "pg";

export type Saved = { id: string; created_at: string | Date };
export type Queryable = { query: (text: string, params: unknown[]) => Promise<{ rows: Saved[] }> };

const INSERT_SQL = `insert into responses (form_version, consent, answers)
                    values ($1, true, $2::jsonb)
                    returning id, created_at`;

let pool: Pool | undefined;

/** Pool pequeno e reaproveitado entre envios (cada instancia serverless abre poucas conexoes). */
export function getPool(rawUrl = process.env.DATABASE_URL): Pool {
  if (!rawUrl) throw new Error("DATABASE_URL ausente");
  if (pool) return pool;
  // O parametro sslmode da URL sobrepoe as opcoes do driver; tiramos e definimos o SSL aqui.
  const u = new URL(rawUrl);
  u.searchParams.delete("sslmode");
  const local = ["localhost", "127.0.0.1", ""].includes(u.hostname) || process.env.DATABASE_SSL === "off";
  pool = new Pool({
    connectionString: u.toString(),
    ssl: local ? false : { rejectUnauthorized: false }, // provedores gerenciados (ex.: Render) usam certificado proprio
    max: 3,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 10_000,
    allowExitOnIdle: true,
  });
  return pool;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Grava uma resposta. Tenta de novo em falhas passageiras (banco reiniciando ou acordando).
 * Uma repeticao rara por gravacao ja confirmada e tratada na analise (respostas identicas em 10 min).
 */
export async function insertResponse(
  db: Queryable,
  formVersion: string,
  answers: Record<string, unknown>,
  opts: { retries?: number; delayMs?: number } = {},
): Promise<Saved> {
  const retries = opts.retries ?? 2;
  const delayMs = opts.delayMs ?? 400;
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await db.query(INSERT_SQL, [formVersion, JSON.stringify(answers)]);
      if (!r.rows[0]) throw new Error("insert sem retorno");
      return r.rows[0];
    } catch (e) {
      if (attempt >= retries) throw e;
      await sleep(delayMs * (attempt + 1));
    }
  }
}
