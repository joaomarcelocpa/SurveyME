"use server";

import { neon } from "@neondatabase/serverless";
import { headers } from "next/headers";
import { after } from "next/server";
import { mirrorToSheet } from "@/lib/sheet";
import { processSubmission, type Result } from "@/lib/submit";

export async function submitSurvey(input: unknown): Promise<Result> {
  const h = await headers();
  // O IP serve so como chave transitoria do rate limit em memoria; nunca e gravado.
  const clientKey = (h.get("x-forwarded-for") ?? "").split(",")[0].trim() || "anon";

  try {
    return await processSubmission(input, {
      open: process.env.SURVEY_OPEN === "true",
      clientKey,
      insert: async (formVersion, answers) => {
        const url = process.env.DATABASE_URL;
        if (!url) throw new Error("DATABASE_URL ausente");
        const sql = neon(url);
        const rows = await sql`insert into responses (form_version, consent, answers)
                  values (${formVersion}, true, ${JSON.stringify(answers)}::jsonb)
                  returning id, created_at`;

        // Copia secundaria na planilha (opcional). Roda depois da resposta ao participante e nunca afeta o envio.
        const sheetUrl = process.env.SHEETS_WEBHOOK_URL;
        const sheetSecret = process.env.SHEETS_WEBHOOK_SECRET;
        const saved = rows[0] as { id: string; created_at: string | Date } | undefined;
        if (sheetUrl && sheetSecret && saved) {
          after(() =>
            mirrorToSheet(
              { id: String(saved.id), createdAt: new Date(saved.created_at).toISOString(), answers },
              { url: sheetUrl, secret: sheetSecret },
            ),
          );
        }
      },
    });
  } catch {
    return { ok: false, error: "Não foi possível salvar agora. Tente novamente." };
  }
}
