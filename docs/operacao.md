# Operação: monitoramento, backup e restauração

## Monitoramento durante a coleta

No painel (`dashboard/`), página **Monitoramento**. Atualiza sozinha a cada minuto e mostra:

- respostas recebidas e válidas contra a meta (60) e o mínimo (50) do protocolo, e o horário da última resposta;
- evolução acumulada e respostas por hora; rajadas (5 ou mais respostas em 5 minutos);
- descartes por motivo, tempo de preenchimento, quase-duplicatas e versões do questionário;
- cobertura por grupo comparado nas QPs (alerta abaixo de 10 respostas válidas por grupo);
- saúde dos dados: conexão e latência do banco, travas de imutabilidade ativas, usuário do painel sem permissão de escrita, idade do último backup e verificação do banco contra esse backup.

Um aviso vermelho de divergência significa que respostas do último backup sumiram do banco ou mudaram. Não sobrescreva backups; investigue antes.

## Backup

Os backups guardam **todas** as respostas (inclusive as que serão descartadas na análise) em arquivos JSONL com um `manifest.json` (contagem, última data, hash SHA-256 do arquivo e hash do estado). Ficam **fora do repositório**, que é público.

### Preparação (uma vez)

```bash
mkdir -p ~/survey-backups && chmod 700 ~/survey-backups
cat > ~/.survey-backup.env <<'ENV'
DATABASE_URL_RO=postgresql://survey_ro:SENHA@HOST/neondb?sslmode=require
SURVEY_BACKUP_DIR=/home/USUARIO/survey-backups
SURVEY_BACKUP_MIRROR=/caminho/da/pasta-do-grupo
ENV
chmod 600 ~/.survey-backup.env
```

`SURVEY_BACKUP_MIRROR` é a cópia para a pasta compartilhada do grupo (por exemplo, uma pasta sincronizada com nuvem). Ela deve ter acesso restrito ao grupo e ao professor.

### Rodar

```bash
scripts/backup.sh                       # verifica contra o último backup e grava um novo se algo mudou
dashboard/.venv/bin/python scripts/backup.py --verify-only
```

Códigos de saída: 0 ok, 1 divergência (respostas sumiram ou mudaram, ou o arquivo de backup foi alterado), 2 falha de leitura ou de cópia. Dois backups nunca se sobrescrevem, e se nada mudou nenhum arquivo novo é criado.

### Agendar a cada hora

```bash
crontab -e
```
```
0 * * * * /home/USUARIO/SurveyME/scripts/backup.sh >> /home/USUARIO/survey-backups/backup.log 2>&1
```

Só roda com o computador ligado. Confira o horário do último backup na página Monitoramento (alerta acima de 3 horas) e rode o comando manualmente antes de eventos importantes.

## Restauração

Em caso de perda ou corrupção do banco, crie um banco novo, aplique as migrations (`db/README.md`) e carregue o backup mais recente:

```bash
DATABASE_URL_ADMIN='postgresql://...' dashboard/.venv/bin/python scripts/restore.py ~/survey-backups/responses-XXXX.jsonl          # simulação
DATABASE_URL_ADMIN='postgresql://...' dashboard/.venv/bin/python scripts/restore.py ~/survey-backups/responses-XXXX.jsonl --yes
```

O script confere o hash do arquivo contra o manifesto, insere sem apagar nem alterar nada (respostas com o mesmo `id` são ignoradas, então pode rodar de novo) e ao final confere que cada resposta existe no banco com conteúdo idêntico.

## Outras camadas

- **Neon:** restauração a um ponto no tempo e branches. A janela de retenção no plano gratuito é curta, então não substitui o backup em arquivo.
- **Cópia no Google Sheets:** o código do formulário pode enviar cada resposta a uma planilha (`SHEETS_WEBHOOK_URL`), mas o script receptor não está mais no repositório. Se for usada, o termo de consentimento deve citar essa cópia.

## Privacidade e prazo

Os arquivos de backup têm as mesmas respostas do banco: sem identificadores, mas com o campo aberto (Q20), que é texto livre. Mantenha-os apenas em locais de acesso restrito e **apague todas as cópias (pasta local, pasta do grupo) até 31/12/2026**, como prevê o protocolo.
