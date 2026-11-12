"use server";

import { headers } from "next/headers";
import { after } from "next/server";
import { getPool, insertResponse } from "@/lib/db";
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
        const saved = await insertResponse(getPool(), formVersion, answers);

        // Copia secundaria na planilha (opcional). Roda depois da resposta ao participante e nunca afeta o envio.
        const sheetUrl = process.env.SHEETS_WEBHOOK_URL;
        const sheetSecret = process.env.SHEETS_WEBHOOK_SECRET;
        if (sheetUrl && sheetSecret) {
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
