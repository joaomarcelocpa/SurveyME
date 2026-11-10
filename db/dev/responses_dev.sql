-- SOMENTE DESENVOLVIMENTO LOCAL. Nunca aplicar no banco de producao.
-- Dados sinteticos para testar o dashboard; nao representam coleta real.
create extension if not exists pgcrypto;

create table if not exists responses_dev (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  form_version text not null,
  consent boolean not null,
  answers jsonb not null
);
