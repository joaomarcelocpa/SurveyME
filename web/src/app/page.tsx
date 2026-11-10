import Survey from "@/components/Survey";

export const dynamic = "force-dynamic";

export default function Page() {
  if (process.env.SURVEY_OPEN !== "true") {
    return (
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-6">
        <h1 className="text-3xl font-medium leading-tight">Pesquisa ainda não aberta</h1>
        <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--muted)" }}>
          Volte em breve. Esta página receberá respostas assim que a coleta começar.
        </p>
      </main>
    );
  }
  return <Survey />;
}
