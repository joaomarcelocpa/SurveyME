-- Cria o usuario somente leitura usado pelo dashboard.
-- Uso: psql "$DATABASE_URL_ADMIN" -v ro_password="'<senha>'" -f db/create_readonly_user.sql
-- A senha e passada na linha de comando; nao a registre no repositorio.
create role survey_ro login password :ro_password;
select current_database() as dbname \gset
grant connect on database :"dbname" to survey_ro;
grant usage on schema public to survey_ro;
grant select on responses to survey_ro;
