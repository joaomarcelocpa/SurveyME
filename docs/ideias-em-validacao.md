# Ideias em validação com o professor

Itens que **não** estão implementados e dependem de aprovação antes de entrarem no protocolo.

## Hash de e-mail para limitar uma resposta por pessoa

**Problema.** O formulário próprio não tem o limite de uma resposta por pessoa do Google Forms, que depende de login. Hoje há apenas o marcador no navegador, o limite diário por rede e a sinalização de quase-duplicatas, todos contornáveis.

**Ideia.** Pedir um e-mail (por exemplo institucional), confirmar por link e guardar somente um código irreversível dele (HMAC com segredo mantido fora do banco), em uma tabela separada das respostas, com restrição de unicidade. O e-mail em si não seria gravado.

**Possível desenho.**
1. A pessoa informa o e-mail; um link de uso único é enviado.
2. Ao abrir o link, o servidor calcula `HMAC(segredo, e-mail normalizado)` e tenta inserir em `participantes(hash)` (único).
3. Se inseriu, libera o formulário; se já existe, informa que já houve participação.
4. As respostas continuam em `responses`, sem chave estrangeira para `participantes` e sem horário em `participantes`, para dificultar o cruzamento por tempo.

**Prós.** Limita de forma real a uma resposta por pessoa; mantém as respostas sem identificador.

**Contras e riscos.**
- Contradiz o protocolo atual ("sem coleta de e-mail e sem exigir login") e o termo de consentimento; exigiria revisar ambos.
- Pela LGPD, o código derivado do e-mail é dado pseudonimizado, não anônimo: quem tiver o segredo e uma lista de e-mails consegue confirmar quem participou (não o que respondeu).
- Exige serviço de envio de e-mail e adiciona atrito, o que pode reduzir a taxa de resposta, num público já pequeno (meta de 60).
- Há risco de reidentificação por cruzamento de horários se as duas tabelas guardarem datas.
- Divulgação por WhatsApp e Instagram: parte do público pode desistir ao ver pedido de e-mail.

**Perguntas para o professor.**
1. Um identificador pseudonimizado (hash de e-mail) é aceitável para pesquisa anônima neste trabalho, ou o anonimato deve ser total?
2. O comitê ou as normas da instituição exigem algo adicional nesse caso?
3. Prefere que a limitação seja tratada só como ameaça à validade, sem mecanismo técnico?

**Decisão:** pendente.
