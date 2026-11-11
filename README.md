# Assistentes de IA no Aprendizado de Programação: Confiança e Dependência Percebidas por Estudantes de Computação

Trabalho prático de **Medição e Experimentação em Engenharia de Software**

## Sobre o trabalho

O grupo planejou e executou uma **survey** para investigar o uso de assistentes de IA generativa (ChatGPT, Copilot, Claude, Gemini etc.) no aprendizado de programação.

**Tema:** *Assistentes de IA no Aprendizado de Programação: Confiança e Dependência Percebidas por Estudantes de Computação.*

**Público-alvo:** estudantes de graduação em computação ou áreas afins que já usaram IA para estudar programação.

**Amostragem:** não probabilística, por conveniência e bola de neve, com divulgação por WhatsApp e outros canais.

### Questões de pesquisa

1. A frequência de uso de IA se associa à confiança em programar sem IA?
2. A dependência percebida da IA varia entre estudantes de períodos diferentes do curso (início, meio e fim)?
3. Quem usa IA para gerar código (sem usá-la para tirar dúvidas) difere, quanto à confiança, de quem a usa para tirar dúvidas e obter explicações (sem gerar código)?

### Métricas

- **Confiança percebida:** média dos itens Q10–Q13 (Likert de 5 pontos).
- **Dependência percebida:** média dos itens Q14–Q17, com Q17 invertido (Likert de 5 pontos).
- **Variáveis de contexto:** frequência de uso (Q6), usos da IA (Q9) e período do curso (Q3).

## Equipe

Bernardo de Resende, Flávio de Souza, João Marcelo Carvalho, Luidi Cadete e Miguel Figueiredo.

## Infraestrutura do survey

Monorepo com duas aplicações e uma fonte única do instrumento.

| Pasta | Conteúdo |
|---|---|
| `questionnaire.json` | Itens, escalas, construtos, QPs e parâmetros; usado pelo formulário e pelo dashboard |
| `web/` | Formulário (Next.js, TypeScript, Tailwind), deploy na Vercel |
| `dashboard/` | Painel de análise (Streamlit, pandas, scipy, pingouin, plotly) |
| `db/` | Migrations SQL, script do usuário somente leitura e tabela de desenvolvimento |
| `scripts/traceability.py` | Gera a tabela de rastreabilidade (item, QP, métrica, escala) em Markdown |
| `deviations.md` | Desvios em relação ao protocolo (exibido no painel) |

### Banco (Neon)

```bash
psql "$DATABASE_URL_ADMIN" -f db/migrations/001_responses.sql
psql "$DATABASE_URL_ADMIN" -f db/migrations/002_imutabilidade.sql
psql "$DATABASE_URL_ADMIN" -v ro_password="'SENHA'" -f db/create_readonly_user.sql
```

As respostas são imutáveis (UPDATE, DELETE e TRUNCATE bloqueados). O descarte é calculado na análise, com motivo. Não se grava IP, user-agent, e-mail nem identificador; o tempo de preenchimento fica em `answers.duration_s`.

### Formulário (`web/`)

```bash
cd web && cp .env.example .env.local   # preencha as variáveis
npm install
npm run dev
npm test
```

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | String de conexão *pooled* do Neon, com permissão de INSERT em `responses` |
| `SURVEY_OPEN` | `false` mostra "Pesquisa ainda não aberta" e recusa gravações; use `true` somente após a entrega do protocolo |
| `NEXT_PUBLIC_CONTACT_EMAIL` | Contato opcional exibido no termo de consentimento |

Deploy: importe o repositório na Vercel com *Root Directory* `web` (mantenha habilitado o acesso a arquivos fora do diretório raiz, pois o build copia `questionnaire.json`) e defina as variáveis acima. A repetição por pessoa é tratada por um marcador no próprio aparelho (localStorage e cookie): quem já respondeu vê "Você já respondeu" e só segue se indicar que é outra pessoa. Não há limite por rede, porque muitos participantes podem dividir o mesmo Wi-Fi. Existe apenas um freio anti-inundação em memória (100 envios por 10 minutos por origem, por instância), contra automação. Quem limpa os dados do navegador ou usa outro aparelho ainda pode repetir; isso é tratado na análise (descarte de idênticas e sinalização de quase-duplicatas).

### Painel (`dashboard/`)

```bash
cd dashboard
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL_RO com o usuário survey_ro
set -a; . ./.env; set +a
.venv/bin/streamlit run app.py
.venv/bin/python -m pytest tests
```

Para testar sem banco, gere dados **sintéticos** e aponte para eles:

```bash
.venv/bin/python seed_dev.py                                  # grava dashboard/data/seed_dev.csv
SURVEY_SOURCE=csv:data/seed_dev.csv .venv/bin/streamlit run app.py
```

`seed_dev.py --db` grava apenas em `responses_dev` (via `DATABASE_URL_DEV`). Esses dados não representam coleta real e não devem ser usados em produção; o painel exibe um aviso quando os detecta.

A exportação de CSV traz todas as respostas, com data e hora, sem dado pessoal. O campo aberto (Q19) é texto livre e deve ser revisado antes de qualquer divulgação.

### Tabela de rastreabilidade

```bash
python scripts/traceability.py > rastreabilidade.md
```
