"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { submitSurvey } from "@/app/actions";
import { itemsInOrder, questionnaire, type Item } from "@/lib/questionnaire";

type Value = string | number | string[];
type Answers = Record<string, Value>;
type Phase = "consent" | "questions" | "submitting" | "done" | "ineligible" | "already";

const MARK = "survey_respondido";
const readMark = () => { try { return localStorage.getItem(MARK) === questionnaire.version || document.cookie.includes(`${MARK}=1`); } catch { return false; } };
const writeMark = () => {
  try { localStorage.setItem(MARK, questionnaire.version); } catch {}
  try { document.cookie = `${MARK}=1; max-age=31536000; path=/; SameSite=Lax`; } catch {}
};

const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL;
const letter = (i: number) => String.fromCharCode(65 + i);

export default function Survey() {
  const [phase, setPhase] = useState<Phase>("consent");
  const [agreed, setAgreed] = useState(false);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [error, setError] = useState<string | null>(null);
  const [website, setWebsite] = useState(""); // honeypot
  const startedAt = useRef(0);
  const focusRef = useRef<HTMLElement | null>(null);
  const mounted = useRef(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => { if (readMark()) setPhase("already"); }, []);

  const item = itemsInOrder[step];
  const total = itemsInOrder.length;
  const value = answers[item?.id];
  const progress = phase === "consent" ? 0 : phase === "done" ? 100 : (step / total) * 100;

  const answered = useMemo(() => {
    if (!item) return false;
    if (!item.required) return true;
    if (item.type === "multi") return Array.isArray(value) && value.length > 0;
    return value !== undefined && value !== "";
  }, [item, value]);

  // Leitor de tela: ao mudar de tela, leva o foco ao titulo e atualiza o titulo da aba.
  useEffect(() => {
    if (phase === "questions") document.title = `Pergunta ${step + 1} de ${total} · ${questionnaire.title}`;
    else if (phase === "done") document.title = `Obrigado · ${questionnaire.title}`;
    else document.title = questionnaire.title;
    if (mounted.current) focusRef.current?.focus();
    mounted.current = true;
  }, [phase, step, total]);

  function set(id: string, v: Value) {
    setAnswers((a) => ({ ...a, [id]: v }));
    setError(null);
    setNotice(null);
  }

  function toggle(it: Item, v: string | number) {
    if (it.type === "multi") {
      const cur = Array.isArray(answers[it.id]) ? (answers[it.id] as string[]) : [];
      set(it.id, cur.includes(v as string) ? cur.filter((x) => x !== v) : [...cur, v as string]);
    } else set(it.id, v);
  }

  async function next() {
    if (phase !== "questions") return;
    if (!answered) {
      setNotice(item.type === "multi" ? "Escolha ao menos uma opção para continuar." : "Escolha uma opção para continuar.");
      return;
    }
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
    if (res.ok) {
      writeMark();
      setPhase("done");
    }
    else {
      setError(res.error);
      setPhase("questions");
    }
  }

  // Teclado: Enter continua; letras ou numeros escolhem a opcao.
  useEffect(() => {
    if (phase !== "questions" || !item) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "TEXTAREA" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "BUTTON" && answered) {
        e.preventDefault();
        void next();
        return;
      }
      const opts = item.options ?? [];
      if (!opts.length) return;
      const idx = item.type === "likert" ? Number(e.key) - 1 : e.key.length === 1 ? e.key.toUpperCase().charCodeAt(0) - 65 : -1;
      if (idx >= 0 && idx < opts.length && (item.type === "likert" ? /^\d$/.test(e.key) : /^[a-z]$/i.test(e.key))) {
        toggle(item, opts[idx].value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <>
      <div className="fixed inset-x-0 top-0 z-10 h-[3px]" style={{ background: "var(--line)" }} role="progressbar" aria-valuenow={Math.round(progress)} aria-valuemin={0} aria-valuemax={100} aria-valuetext={phase === "questions" || phase === "submitting" ? `Pergunta ${step + 1} de ${total}` : `${Math.round(progress)}%`} aria-label="Progresso">
        <div className="h-full transition-[width] duration-500" style={{ width: `${progress}%`, background: "var(--accent)" }} />
      </div>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-6 py-10 sm:px-8">
        <div key={`${phase}-${step}`} className="fade">
          {phase === "consent" && (
            <div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>Pesquisa acadêmica · cerca de 5 minutos</p>
              <h1 ref={(el) => { if (phase === "consent") focusRef.current = el; }} tabIndex={-1} className="mt-4 text-4xl font-medium leading-[1.1] tracking-tight sm:text-5xl">{questionnaire.title}</h1>
              <p className="mt-5 max-w-xl text-lg leading-relaxed" style={{ color: "var(--muted)" }}>
                Queremos entender como estudantes de computação usam assistentes de IA nos estudos de programação.
              </p>

              <h2 className="mt-12 text-sm font-medium" style={{ color: "var(--muted)" }}>Termo de consentimento</h2>
              <dl className="mt-3 border-t text-base leading-relaxed" style={{ borderColor: "var(--line)" }}>
                {[
                  ["Finalidade", "Trabalho acadêmico da disciplina de Medição e Experimentação em Engenharia de Software, sobre o uso de IA no aprendizado de programação."],
                  ["Anonimato", "Não coletamos nome, e-mail, IP nem qualquer dado que identifique você. Os resultados serão apresentados de forma agregada. Para evitar envios repetidos, guardamos apenas um marcador no seu próprio aparelho (cookie e armazenamento local do navegador), que não é ligado às suas respostas e não identifica você."],
                  ["Voluntariedade", "A participação é voluntária. Você pode desistir a qualquer momento fechando a página."],
                  ["Armazenamento", "As respostas ficam em um banco de dados com acesso restrito aos integrantes do grupo e ao professor, não são publicadas e serão mantidas até o fim da disciplina (31/12/2026)."],
                  ["Contato", CONTACT ? CONTACT : "Fale com o grupo pelo canal em que recebeu este link."],
                ].map(([t, d]) => (
                  <div key={t} className="grid gap-1 border-b py-4 sm:grid-cols-[9rem_1fr] sm:gap-6" style={{ borderColor: "var(--line)" }}>
                    <dt className="font-medium">{t}</dt>
                    <dd style={{ color: "var(--muted)" }}>
                      {t === "Contato" && CONTACT ? <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a> : d}
                    </dd>
                  </div>
                ))}
              </dl>

              <label className="mt-8 flex cursor-pointer items-start gap-3">
                <input type="checkbox" className="peer sr-only" checked={agreed} onChange={(e) => { setAgreed(e.target.checked); setNotice(null); }} />
                <span
                  className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-[4px] border peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[var(--accent)]"
                  style={{ borderColor: agreed ? "var(--accent)" : "var(--muted)", background: agreed ? "var(--accent)" : "transparent", color: "var(--on-accent)" }}
                  aria-hidden
                >
                  {agreed && <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none"><path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
                </span>
                <span className="text-base">Li o termo e concordo em participar desta pesquisa.</span>
              </label>
              <Honeypot value={website} onChange={setWebsite} />
              <button
                className="mt-8 rounded-lg px-6 py-3 text-base font-medium transition-opacity"
                style={{ background: "var(--ink)", color: "var(--bg)", opacity: agreed ? 1 : 0.55 }}
                aria-disabled={!agreed}
                onClick={() => {
                  if (!agreed) { setNotice("Marque a caixa de concordância para começar."); return; }
                  startedAt.current = Date.now();
                  setPhase("questions");
                }}
              >
                Começar
              </button>
              {notice && <p role="alert" className="mt-4 text-sm" style={{ color: "var(--danger)" }}>{notice}</p>}
            </div>
          )}

          {(phase === "questions" || phase === "submitting") && item && (
            <div>
              <p aria-hidden className="text-sm tabular-nums" style={{ color: "var(--muted)" }}>{step + 1} / {total}</p>
              <fieldset ref={(el) => { focusRef.current = el; }} tabIndex={-1} className="mt-4">
                <legend className="text-[1.65rem] font-medium leading-snug tracking-tight sm:text-3xl">
                  <span className="sr-only">Pergunta {step + 1} de {total}. {item.required ? "Resposta obrigatória. " : "Resposta opcional. "}</span>
                  {item.text}
                </legend>
                {item.type === "multi" && <p className="mt-2 text-sm" style={{ color: "var(--muted)" }}>Escolha quantas quiser.</p>}
                <Field item={item} value={value} onPick={(v) => toggle(item, v)} onText={(v) => set(item.id, v)} />
              </fieldset>

              {(error || notice) && <p role="alert" className="mt-5 text-sm" style={{ color: "var(--danger)" }}>{error ?? notice}</p>}

              <div className="mt-10 flex items-center gap-5">
                <button
                  className="rounded-lg px-6 py-3 text-base font-medium transition-opacity"
                  style={{ background: "var(--ink)", color: "var(--bg)", opacity: answered ? 1 : 0.55 }}
                  aria-disabled={!answered || phase === "submitting"}
                  onClick={() => { if (phase !== "submitting") void next(); }}
                >
                  {phase === "submitting" ? "Enviando…" : step === total - 1 ? "Enviar respostas" : "Continuar"}
                </button>
                {step > 0 && (
                  <button className="min-h-11 px-2 text-base underline-offset-4 hover:underline" style={{ color: "var(--muted)" }} disabled={phase === "submitting"} onClick={() => setStep(step - 1)}>
                    Voltar
                  </button>
                )}
                <span aria-hidden className="ml-auto hidden text-sm sm:inline" style={{ color: "var(--muted)" }}>Enter ↵</span>
              </div>
            </div>
          )}

          {phase === "already" && (
            <div>
              <h1 ref={(el) => { if (phase === "already") focusRef.current = el; }} tabIndex={-1} className="text-3xl font-medium leading-tight">Você já respondeu esta pesquisa</h1>
              <p className="mt-4 max-w-xl text-lg leading-relaxed" style={{ color: "var(--muted)" }}>
                Este aparelho já enviou uma resposta. Cada pessoa participa uma vez; obrigado pela contribuição.
              </p>
              <button className="mt-8 min-h-11 text-base underline underline-offset-4" style={{ color: "var(--muted)" }} onClick={() => setPhase("consent")}>
                Outra pessoa vai responder neste aparelho
              </button>
            </div>
          )}

          {phase === "ineligible" && (
            <div>
              <h1 ref={(el) => { if (phase === "ineligible") focusRef.current = el; }} tabIndex={-1} className="text-3xl font-medium leading-tight">Obrigado pelo interesse</h1>
              <p className="mt-4 max-w-xl text-lg leading-relaxed" style={{ color: "var(--muted)" }}>
                Esta pesquisa é voltada a estudantes de graduação em computação ou áreas afins que já usaram IA para estudar programação. Nenhuma resposta foi registrada.
              </p>
            </div>
          )}

          {phase === "done" && (
            <div>
              <h1 ref={(el) => { if (phase === "done") focusRef.current = el; }} tabIndex={-1} className="text-4xl font-medium leading-tight tracking-tight">Obrigado por participar.</h1>
              <p className="mt-4 max-w-xl text-lg leading-relaxed" style={{ color: "var(--muted)" }}>
                Sua resposta foi registrada de forma anônima. Se puder, compartilhe o link com colegas de computação: quanto mais respostas, mais confiáveis os resultados.
              </p>
            </div>
          )}
        </div>
      </main>
    </>
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

function Field({ item, value, onPick, onText }: { item: Item; value: unknown; onPick: (v: string | number) => void; onText: (v: string) => void }) {
  if (item.type === "open") {
    const text = (value as string) ?? "";
    return (
      <div className="mt-8">
        <textarea
          className="w-full resize-none border-b-2 bg-transparent py-2 text-lg leading-relaxed outline-none placeholder:opacity-70 focus:border-[var(--accent)]"
          style={{ borderColor: "var(--muted)" }}
          aria-label={item.text}
          rows={4}
          maxLength={item.max_length}
          placeholder="Escreva aqui (opcional)"
          value={text}
          onChange={(e) => onText(e.target.value)}
        />
        <p aria-hidden className="mt-1 text-right text-sm tabular-nums" style={{ color: "var(--muted)" }}>{text.length}/{item.max_length}</p>
      </div>
    );
  }

  const multi = item.type === "multi";
  return (
    <div className="mt-8 border-t" style={{ borderColor: "var(--line)" }}>
      {(item.options ?? []).map((o, i) => {
        const on = multi ? Array.isArray(value) && value.includes(o.value as string) : value === o.value;
        const key = item.type === "likert" ? String(i + 1) : letter(i);
        return (
          <label key={String(o.value)} className="block cursor-pointer">
            <input type={multi ? "checkbox" : "radio"} name={item.id} className="peer sr-only" checked={on} onChange={() => onPick(o.value)} />
            <span
              className="flex items-center gap-4 border-b px-1 py-3.5 text-lg transition-colors hover:bg-[var(--hover)] peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:-outline-offset-2 peer-focus-visible:outline-[var(--accent)]"
              style={{ borderColor: "var(--line)", color: on ? "var(--accent)" : "var(--ink)" }}
            >
              <span
                aria-hidden
                className="grid h-6 w-6 shrink-0 place-items-center rounded-[4px] border text-xs font-medium"
                style={{ borderColor: on ? "var(--accent)" : "var(--line)", background: on ? "var(--accent)" : "transparent", color: on ? "var(--on-accent)" : "var(--muted)" }}
              >
                {key}
              </span>
              <span className="flex-1">{o.label}</span>
              {on && <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden><path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
            </span>
          </label>
        );
      })}
    </div>
  );
}
