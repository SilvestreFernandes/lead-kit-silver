# Lead Kit Silver: instruções para o Claude Code

Idioma do projeto: **português do Brasil**, tom simples e direto. Nunca use travessão (o traço longo) em nenhum texto. Reescreva com vírgula ou ponto.

## O que é este projeto

Toolkit vendido por R$ 97 (Kiwify) que faz a IA do comprador (Claude Code, Codex e similares) instalar no computador dele uma ferramenta de busca de leads no Google Maps. A IA entrevista o dono do negócio, grava um perfil, e um painel local mostra os leads com nota e mensagem de abordagem prontas. O produto anterior, o ebook "IA na Real", está pausado e não faz parte deste repositório.

Dono: Silvestre Fernandes Silva (Brasília), estudante de Bacharelado em Inteligência Artificial no CEUB e CEO da BrandForge. Cliente ideal: quem vende sites, IA ou automação pra negócios locais, mas o kit deve funcionar pra qualquer negócio e nicho.

## Leia antes de qualquer código

1. `docs/planejamento/arquitetura.md`: estrutura, componentes, API, painel, fases e critérios de pronto.
2. `docs/planejamento/entrevista-e-perfil.md`: as 12 perguntas, o formato do `perfil.json`, regras de nota, modelos de mensagem e validação.
3. `docs/planejamento/fase0-verificacao-motor.md`: o que foi verificado do motor na fase 0 (versão, execução, colunas, API).
4. `docs/planejamento/licoes-instalacao.md`: lições do teste em máquina limpa, que alimentam o prompt de instalação e o guia do cliente.

Os dois primeiros documentos são a especificação. Em caso de dúvida, eles mandam. Se algo neles estiver errado ou faltando, pare e pergunte antes de decidir.

## Como trabalhar

- Siga as fases do plano, uma de cada vez. Ao terminar uma fase, mostre como o Silvestre testa no Windows e espere o ok antes de seguir.
- Só biblioteca padrão do Python 3.10+. Painel em HTML, CSS e JavaScript puros, sem framework, sem build e sem npm.
- Testes automatizados pra tudo que for lógica (nota, validação, modelos, rotas). Rodam sem rede, com `python -m unittest`.
- Não invente nomes de coluna do CSV do motor nem parâmetros da API dele. Confira na documentação do motor e com uma execução real.
- Windows é o sistema testado. Nada de depender de bash: scripts em Python, mais `iniciar.bat` e `iniciar.sh`.
- Nomes de arquivo e pasta em português, sem acento.
- Textos que a pessoa lê (painel, mensagens de erro, guias) em português simples, sem jargão.

## Regras que não podem ser quebradas

- O motor `gosom/google-maps-scraper` roda sem alteração, com versão fixada, só em `127.0.0.1`. Nunca exponha o servidor fora de `127.0.0.1`.
- Mantenha `LICENSE` e `CREDITS.md` (MIT do kit base de Mahan e do motor de Georgios Komninos).
- O painel nunca chama IA. IA só entra na instalação e na entrevista. Nota e mensagem saem de regras e modelos salvos.
- O servidor local valida `Host`, exige token nas rotas que alteram dados e não libera CORS.
- Nenhum dado de lead sai do computador da pessoa. Sem telemetria.
- O prompt de instalação nunca manda desligar antivírus, firewall ou permissões de segurança da ferramenta de IA, e pede confirmação antes de cada passo que muda o computador. Ele instala o que faltar (Python e, se preciso, Docker), é retomável depois de reinício e nunca promete instalação sem problemas.
- Sem promessa de renda, sem escassez falsa, sem depoimentos inventados em qualquer texto de venda.
- O kit só afirma o que foi testado. Se não foi testado em um sistema ou ferramenta, não entra no material.
- Não copie texto, imagens, nome ou logo do produto do mentor.
- Nunca faça commit de CSV nem de dados de leads reais. Testes usam só dados fictícios.

## Decisões já tomadas

- Motor: o Docker é o caminho principal. Rodar o motor como programa direto, sem Docker, é pesquisa futura e fica fora da v1.

## Decisões em aberto (pare e pergunte)

Não decida sozinho: texto da licença da camada paga, nome do produto, parcelamento no Kiwify, pesos padrão das regras de nota, e qualquer mudança nas 12 perguntas.

## Estado do projeto

A fase 0 (verificação do motor em Docker) está concluída. A próxima é a fase 1.

## Dados e privacidade durante o desenvolvimento

`dados/` está no `.gitignore`. Nunca faça commit de `perfil.json`, `leads.db` ou exportações. Use só dados fictícios em testes.
