-- Tabela de respostas do survey. Anonimato total: nenhum identificador.
create extension if not exists pgcrypto;

create table if not exists responses (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  form_version text not null,
  consent boolean not null,
  answers jsonb not null
);

comment on table responses is 'Respostas brutas. Nunca deletar: o descarte e calculado na analise.';
comment on column responses.answers is 'Chaves = ids do questionnaire.json; duration_s = tempo de preenchimento em segundos.';
