# Product

<!-- impeccable:product-schema 1 -->

> Arquivo de apoio ao desenvolvimento do painel. Não faz parte do pacote do produto vendido.

## Platform

web

## Stack
HTML, CSS e JavaScript puros, escolha já tomada: sem framework, sem build, sem npm. O painel é servido por um servidor local em Python (somente biblioteca padrão) em 127.0.0.1. Não há deploy: o painel roda no computador de quem comprou.

## Users
Pessoas que vendem sites, IA ou automação para negócios locais (agências pequenas, freelancers, quem está começando). Muitas não têm formação técnica. Usam Windows, abrem o painel no navegador a partir de um programa que a IA delas instalou, e nunca abriram um terminal. O trabalho delas: achar negócios do bairro ou da cidade que combinam com o que vendem, ver quais valem a abordagem primeiro e mandar uma mensagem pessoal, uma por vez.

## Product Purpose
Mostrar, em um painel local, negócios do Google Maps com nota (A, B ou C) e mensagem de abordagem prontas, calculadas por regras e modelos salvos, sem IA e sem enviar nenhum dado para fora do computador. Sucesso é a pessoa abrir o painel, entender o que fazer sem ajuda e fazer o primeiro contato com um negócio que faça sentido. Não é medido em quantidade de leads nem em renda.

## Positioning
O kit instala sozinho pela IA da própria pessoa, roda tudo localmente (leads, notas e mensagens ficam no computador) e explica cada nota em frases simples, com os pontos de cada motivo. Uma ferramenta online de leads não pode afirmar que os dados nunca saem da máquina.

## Operating Context
Windows. Navegador comum. O painel fica aberto ao lado do WhatsApp Web e do e-mail. O motor de busca roda em Docker Desktop, e a pessoa pode precisar ligar o Docker ou o motor. Planilhas .xlsx e .csv são abertas no Excel ou no Google Planilhas. A entrevista que gera o perfil acontece na IA da pessoa, fora do painel.

## Capabilities and Constraints
- Três telas: Buscar, Leads e Minha oferta.
- O painel nunca chama IA. Nota e mensagem saem de regras e modelos salvos.
- O servidor escuta só em 127.0.0.1, valida o Host, exige token para escrever e não libera CORS.
- Tudo local: nenhum pedido externo do painel, sem fontes do Google, sem CDN. Só o nome da cidade e o estado vão ao serviço OpenStreetMap, e isso é dito na tela.
- Sem botão de cancelar busca (o motor não tem cancelamento confirmado).
- Busca ampla ainda não medida: aparece como "em breve".
- Testes que continuam valendo em qualquer visual: nada de innerHTML, nada de fetch fora de api.js, nada de URL externa, nada de travessão.
- Acessibilidade com leitor de tela não foi testada. Nenhum texto pode afirmar acessibilidade antes disso.

## Brand Commitments
- Identidade: prata e grafite. Minimalista e limpo. Tema claro e escuro.
- Português do Brasil, simples e direto, sem jargão.
- Nunca usar travessão (o traço longo) em nenhum texto. Usar vírgula ou ponto.
- Nome do produto ainda em aberto (hoje "Lead Kit Silver"). Não decidir sozinho.

## Evidence on Hand
Não existem depoimentos, clientes, números de resultado nem casos. Nada disso pode ser inventado. Os únicos números medidos (negócios por busca, tempos) ficam na documentação interna e não entram na tela como promessa. Prints reais do painel com dados fictícios estão em prints/ (não versionado).

## Product Principles
1. Honestidade antes de convencer: sem promessa de renda, de quantidade ou de resultado, sem escassez falsa, e o painel só afirma o que foi testado.
2. Quem nunca abriu um terminal precisa conseguir seguir: toda instrução diz onde e como, em palavras simples.
3. Tudo fica no computador da pessoa, e a tela diz isso com fatos, não com slogans.
4. Cada nota se explica: a pessoa vê por que o negócio é A, B ou C.
5. O envio é sempre manual e pessoal, um negócio por vez: o painel ajuda a ler e preparar, nunca a disparar em massa.

## Accessibility & Inclusion
Público com pouca familiaridade técnica: texto simples, instruções passo a passo, alvos de clique grandes o bastante e contraste suficiente nos dois temas. Leitor de tela ainda não testado (ver Capabilities and Constraints).
