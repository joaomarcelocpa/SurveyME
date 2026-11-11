# Desvios em relação ao protocolo

Registro de tudo que mudou entre o protocolo pré-registrado e a execução. Cada entrada traz a mudança e o motivo.

| # | Data | O que mudou | Por quê |
|---|------|-------------|---------|
| 1 | 2026-11-10 | O instrumento passou a ser um formulário web próprio (Next.js, com gravação em banco Postgres), em vez do Google Forms citado no protocolo. | Controle do fluxo (consentimento, filtros de elegibilidade, ordem alternada dos itens), tempo de preenchimento e exportação com data e hora. O conteúdo dos itens, as escalas e os códigos Q1–Q19 não mudaram. |
| 2 | 2026-11-10 | Inclusão do critério de descarte "tempo de preenchimento muito curto" (menos de 60 s), ausente da lista de descartes do protocolo. | O formulário registra o tempo de preenchimento; respostas muito mais rápidas que o tempo médio do pré-teste (cerca de 5 min) indicam marcação automática. O limiar é um parâmetro (`min_duration_seconds` em `questionnaire.json`) e o efeito do critério é reportado no painel. |
| 3 | 2026-11-10 | Medidas contra respostas repetidas: marcador no próprio aparelho (localStorage e cookie, sem dado pessoal) e sinalização, no painel, de respostas quase idênticas para revisão manual. Não há limite por rede nem contador externo. | O protocolo prevê descartar "duplicadas evidentes", mas o formulário próprio não tem o limite por login do Google Forms (o protocolo já dispensava login). Os mecanismos reduzem a repetição sem identificar ninguém, e não penalizam quem divide a mesma rede; o termo de consentimento descreve o marcador. Limitação: quem limpa os dados do navegador ou usa outro aparelho ainda pode repetir. |

Novos desvios devem ser acrescentados aqui antes da análise final.
