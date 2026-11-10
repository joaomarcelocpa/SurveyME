import Survey from "@/components/Survey";

export const dynamic = "force-dynamic";

export default function Page() {
  if (process.env.SURVEY_OPEN !== "true") {
    return (
      <main className="mx-auto flex min-h-dvh max-w-xl items-center px-5">
        <div className="w-full rounded-3xl p-8 text-center shadow-sm" style={{ background: "var(--card)", border: "1px solid var(--line)" }}>
          <h1 className="text-2xl font-semibold">Pesquisa ainda não aberta</h1>
          <p className="mt-3" style={{ color: "var(--muted)" }}>
            Volte em breve. Esta página receberá respostas assim que a coleta começar.
          </p>
        </div>
      </main>
    );
  }
  return <Survey />;
}
