import { z } from "zod";
import { itemsInOrder, questionnaire, type Item } from "./questionnaire";

function schemaFor(item: Item): z.ZodType {
  const values = (item.options ?? []).map((o) => o.value);
  let s: z.ZodType;
  switch (item.type) {
    case "single":
    case "likert":
      s = z.custom<string | number>((v) => values.includes(v as string | number), "opcao invalida");
      break;
    case "multi":
      s = z
        .array(z.custom<string>((v) => values.includes(v as string), "opcao invalida"))
        .min(1)
        .refine((a) => new Set(a).size === a.length, "duplicado");
      break;
    case "open":
      s = z.string().max(item.max_length ?? 500);
      break;
  }
  return item.required ? s : s.optional();
}

const shape: Record<string, z.ZodType> = {};
for (const it of itemsInOrder) shape[it.id] = schemaFor(it);

export const answersSchema = z.object(shape).strict();

export const submissionSchema = z.object({
  consent: z.literal(true),
  website: z.string().max(0).optional(), // honeypot
  duration_s: z.number().int().min(0).max(86_400),
  answers: answersSchema,
});

export type Submission = z.infer<typeof submissionSchema>;

/** Retorna null se elegivel; senao o id do item de triagem reprovado. */
export function failedScreening(answers: Record<string, unknown>): string | null {
  for (const it of questionnaire.items) {
    if (it.role === "screening" && answers[it.id] !== it.pass_value) return it.id;
  }
  return null;
}
