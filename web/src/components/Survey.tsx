"use client";

import { useMemo, useRef, useState } from "react";
import { submitSurvey } from "@/app/actions";
import { itemsInOrder, questionnaire, type Item } from "@/lib/questionnaire";

type Answers = Record<string, string | number | string[]>;
type Phase = "consent" | "questions" | "submitting" | "done" | "ineligible";

const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

const card = { background: "var(--card)", border: "1px solid var(--line)" } as const;

export default function Survey() {
  const [phase, setPhase] = useState<Phase>("consent");
  const [agreed, setAgreed] = useState(false);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [error, setError] = useState<string | null>(null);
  const [website, setWebsite] = useState(""); // honeypot
  const startedAt = useRef<number>(0);

  const item = itemsInOrder[step];
  const total = itemsInOrder.length;
  const progress = phase === "consent" ? 0 : phase === "done" ? 100 : Math.round((step / total) * 100);

  const value = answers[item?.id];
  const answered = useMemo(() => {
    if (!item) return false;
    if (!item.required) return true;
    if (item.type === "multi") return Array.isArray(value) && value.length > 0;
    return value !== undefined && value !== "";
  }, [item, value]);

  function set(id: string, v: string | number | string[]) {
    setAnswers((a) => ({ ...a, [id]: v }));
    setError(null);
  }

  async function next() {
    if (!answered) return;
    if (item.role === "screening" && answers[item.id] !== item.pass_value) {
      setPhase("ineligible");
      return;
    }
    if (step < total - 1) {
      setStep(step + 1);
      return;
    }
    setPhase("submitting");
    const clean: Answers = { ...answers };
    if (typeof clean.Q19 === "string" && clean.Q19.trim() === "") delete clean.Q19;
    const res = await submitSurvey({
      consent: true,
      website,
      duration_s: Math.round((Date.now() - startedAt.current) / 1000),
      answers: clean,
    });
    if (res.ok) setPhase("done");
    else {
      setError(res.error);
      setPhase("questions");
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col px-5 py-8">
      <div
        className="mb-6 h-2 w-full overflow-hidden rounded-full"
        style={{ background: "var(--brand-soft)" }}
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso"
      >
        <div className="h-full rounded-full transition-all duration-300" style={{ width: `${progress}%`, background: "var(--brand)" }} />
      </div>

      <section className="flex-1 rounded-3xl p-6 shadow-sm sm:p-8" style={card}>
        {phase === "consent" && (
          <div>
            <h1 className="text-2xl font-semibold">{questionnaire.title}</h1>
            <h2 className="mt-5 text-lg font-medium">Termo de Consentimento</h2>
            <ul className="mt-3 space-y-3 text-[15px] leading-relaxed" style={{ color: "var(--muted)" }}>
              <li><strong style={{ color: "var(--ink)" }}>Finalidade.</strong> Trabalho acadêmico da disciplina de Medição e Experimentação em Engenharia de Software, sobre o uso de IA no aprendizado de programação. Leva cerca de 5 minutos.</li>
              <li><strong style={{ color: "var(--ink)" }}>Anonimato.</strong> Não coletamos nome, e-mail, IP nem qualquer dado que identifique você. Os resultados serão apresentados de forma agregada.</li>
              <li><strong style={{ color: "var(--ink)" }}>Voluntariedade.</strong> A participação é voluntária. Você pode desistir a qualquer momento fechando a página.</li>
              <li><strong style={{ color: "var(--ink)" }}>Armazenamento.</strong> As respostas ficam em um banco de dados com acesso restrito aos integrantes do grupo e ao professor, não são publicadas e serão mantidas até o fim da disciplina (31/12/2026).</li>
              <li><strong style={{ color: "var(--ink)" }}>Contato.</strong> {CONTACT ? <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a> : "Fale com o grupo pelo canal em que recebeu este link."}</li>
            </ul>
            <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-2xl p-4" style={{ background: "var(--brand-soft)" }}>
              <input type="checkbox" className="mt-1 h-5 w-5 accent-[var(--brand)]" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
              <span className="text-[15px]">Li e concordo em participar desta pesquisa.</span>
            </label>
            <Honeypot value={website} onChange={setWebsite} />
            <button
              className="mt-6 w-full rounded-2xl px-5 py-3 font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-40"
              style={{ background: "var(--brand)" }}
              disabled={!agreed}
              onClick={() => { startedAt.current = Date.now(); setPhase("questions"); }}
            >
              Começar
            </button>
          </div>
        )}

        {(phase === "questions" || phase === "submitting") && item && (
          <div>
            <p className="text-sm" style={{ color: "var(--muted)" }}>Pergunta {step + 1} de {total}</p>
            <fieldset className="mt-2">
              <legend className="text-xl font-semibold leading-snug">{item.text}</legend>
              <Field item={item} value={value} onChange={(v) => set(item.id, v)} />
            </fieldset>
            {error && <p role="alert" className="mt-4 text-sm text-red-500">{error}</p>}
            <div className="mt-8 flex gap-3">
              {step > 0 && (
                <button
                  className="rounded-2xl px-5 py-3 font-medium"
                  style={{ border: "1px solid var(--line)" }}
                  disabled={phase === "submitting"}
                  onClick={() => setStep(step - 1)}
                >
                  Voltar
                </button>
              )}
              <button
                className="flex-1 rounded-2xl px-5 py-3 font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                style={{ background: "var(--brand)" }}
                disabled={!answered || phase === "submitting"}
                onClick={next}
              >
                {phase === "submitting" ? "Enviando…" : step === total - 1 ? "Enviar" : "Continuar"}
              </button>
            </div>
          </div>
        )}

        {phase === "ineligible" && (
          <div className="text-center">
            <h1 className="text-2xl font-semibold">Obrigado pelo interesse</h1>
            <p className="mt-3" style={{ color: "var(--muted)" }}>
              Esta pesquisa é voltada a estudantes de graduação em computação ou áreas afins que já usaram IA para estudar programação. Nenhuma resposta foi registrada.
            </p>
          </div>
        )}

        {phase === "done" && (
          <div className="text-center">
            <h1 className="text-2xl font-semibold">Obrigado por participar!</h1>
            <p className="mt-3" style={{ color: "var(--muted)" }}>
              Sua resposta foi registrada de forma anônima. Se puder, compartilhe o link com colegas de computação.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}

function Honeypot({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div aria-hidden="true" style={{ position: "absolute", left: "-10000px", width: 1, height: 1, overflow: "hidden" }}>
      <label>
        Não preencha este campo
        <input type="text" name="website" tabIndex={-1} autoComplete="off" value={value} onChange={(e) => onChange(e.target.value)} />
      </label>
    </div>
  );
}

function Field({ item, value, onChange }: { item: Item; value: unknown; onChange: (v: string | number | string[]) => void }) {
  if (item.type === "open") {
    return (
      <textarea
        className="mt-5 w-full rounded-2xl p-4 outline-none focus:ring-2"
        style={{ background: "var(--card)", border: "1px solid var(--line)", ["--tw-ring-color" as string]: "var(--brand)" }}
        rows={4}
        maxLength={item.max_length}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  const multi = item.type === "multi";
  const likert = item.type === "likert";
  const selected = (v: string | number) => (multi ? Array.isArray(value) && value.includes(v as string) : value === v);
  return (
    <div className={likert ? "mt-5 grid gap-2" : "mt-5 grid gap-3"}>
      {(item.options ?? []).map((o) => {
        const on = selected(o.value);
        return (
          <label
            key={String(o.value)}
            className="flex cursor-pointer items-center gap-3 rounded-2xl px-4 py-3 transition"
            style={{ border: `1.5px solid ${on ? "var(--brand)" : "var(--line)"}`, background: on ? "var(--brand-soft)" : "transparent" }}
          >
            <input
              type={multi ? "checkbox" : "radio"}
              name={item.id}
              className="h-5 w-5 accent-[var(--brand)]"
              checked={on}
              onChange={() => {
                if (multi) {
                  const cur = Array.isArray(value) ? (value as string[]) : [];
                  onChange(cur.includes(o.value as string) ? cur.filter((x) => x !== o.value) : [...cur, o.value as string]);
                } else onChange(o.value);
              }}
            />
            <span>{likert ? `${o.value} · ${o.label}` : o.label}</span>
          </label>
        );
      })}
    </div>
  );
}
