import { questionnaire } from "./questionnaire";
import { allow } from "./ratelimit";
import { failedScreening, submissionSchema } from "./validation";

export type Result = { ok: true } | { ok: false; error: string };

export type Deps = {
  open: boolean;
  clientKey: string;
  insert: (formVersion: string, answers: Record<string, unknown>) => Promise<void>;
};

export async function processSubmission(input: unknown, deps: Deps): Promise<Result> {
  if (!deps.open) return { ok: false, error: "A pesquisa ainda não está aberta." };

  // Honeypot: finge sucesso e nao grava.
  const hp = (input as { website?: unknown } | null)?.website;
  if (typeof hp === "string" && hp.length > 0) return { ok: true };

  if (!allow(deps.clientKey)) {
    return { ok: false, error: "Muitas tentativas. Aguarde alguns minutos." };
  }

  const parsed = submissionSchema.safeParse(input);
  if (!parsed.success) return { ok: false, error: "Respostas inválidas ou incompletas." };

  const { answers, duration_s } = parsed.data;
  if (failedScreening(answers)) return { ok: false, error: "Fora da população-alvo." };

  await deps.insert(questionnaire.version, { ...answers, duration_s });
  return { ok: true };
}
