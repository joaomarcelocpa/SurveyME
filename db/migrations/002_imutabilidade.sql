-- Impede alteracao e remocao de respostas (descarte e feito na analise).
create or replace function responses_block_mutation() returns trigger as $$
begin
  raise exception 'responses e append-only: % bloqueado', tg_op;
end;
$$ language plpgsql;

drop trigger if exists responses_no_update_delete on responses;
create trigger responses_no_update_delete
  before update or delete on responses
  for each row execute function responses_block_mutation();

drop trigger if exists responses_no_truncate on responses;
create trigger responses_no_truncate
  before truncate on responses
  for each statement execute function responses_block_mutation();
