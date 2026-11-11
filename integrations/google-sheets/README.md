# Copia das respostas no Google Sheets

Cada resposta gravada no banco também é enviada a uma planilha, no formato do Google Forms (uma linha por
resposta, uma coluna por pergunta, carimbo de data/hora na primeira coluna). **O banco continua sendo a fonte
oficial**: se a planilha falhar, a resposta já está salva e o participante não percebe nada.

## Configuração (uma vez)

1. Crie uma planilha nova no Google Sheets (pode se chamar "Respostas da pesquisa").
2. **Extensões > Apps Script**, apague o conteúdo e cole o arquivo `Code.gs` desta pasta. Salve.
3. **Configurações do projeto (engrenagem) > Propriedades do script > Adicionar propriedade**:
   nome `SECRET`, valor uma senha longa e aleatória (ex.: `openssl rand -hex 24`). Guarde-a.
4. **Implantar > Nova implantação > Tipo: App da Web**. *Executar como*: **Eu**. *Quem tem acesso*: **Qualquer pessoa**.
   Autorize quando pedir (tela "O Google não verificou este app": Avançado > Ir para o projeto). Copie a URL que termina em `/exec`.
   "Qualquer pessoa" vale só para essa URL, que só grava com o `SECRET`; a planilha em si continua privada.
5. Na Vercel (Settings > Environment Variables), crie:
   - `SHEETS_WEBHOOK_URL` = a URL `/exec`
   - `SHEETS_WEBHOOK_SECRET` = o mesmo valor do `SECRET`

   Depois faça **Redeploy**.

## Testar

Antes do site, direto no receptor (cria uma linha de teste; apague-a depois):

```bash
curl -L -X POST "URL_EXEC" -H "Content-Type: text/plain" \
  -d '{"token":"SEU_SECRET","headers":["Carimbo de data/hora","Q1. teste","ID da resposta"],"row":["2026-11-13T12:00:00.000Z","ok","teste-1"]}'
# esperado: {"ok":true}   (com token errado: {"ok":false,"error":"nao autorizado"})
```

Depois envie uma resposta pelo site: a linha aparece na aba "Respostas" em poucos segundos.

## Cuidados

- Compartilhe a planilha só com o grupo e o professor, de preferência como **leitor**. Quem edita pode alterar valores; a versão que vale é a do banco.
- A planilha tem os mesmos dados do banco (sem nome, e-mail ou IP). Não a deixe pública.
- Ao mudar o `Code.gs`, use **Implantar > Gerenciar implantações > editar > Nova versão**; salvar não basta.
- Se o site ficar sem enviar por algum tempo, as respostas continuam no banco; as linhas que faltarem na planilha podem ser reenviadas a partir do banco (o ID da resposta evita duplicar).
