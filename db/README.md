# Banco de dados

Migrations em ordem numerica; aplique com `psql "$DATABASE_URL_ADMIN" -f <arquivo>`.

- `migrations/001_responses.sql`: tabela `responses`.
- `migrations/002_imutabilidade.sql`: bloqueia UPDATE, DELETE e TRUNCATE.
- `create_readonly_user.sql`: usuario `survey_ro` (somente SELECT).
- `dev/responses_dev.sql`: tabela para dados sinteticos, **apenas local**.

Ajuste o nome do banco em `create_readonly_user.sql` se nao for `neondb`.
