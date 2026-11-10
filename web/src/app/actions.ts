"use server";

import { neon } from "@neondatabase/serverless";
import { headers } from "next/headers";
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
        await sql`insert into responses (form_version, consent, answers)
                  values (${formVersion}, true, ${JSON.stringify(answers)}::jsonb)`;
      },
    });
  } catch {
    return { ok: false, error: "Não foi possível salvar agora. Tente novamente." };
  }
}
