# Lições do teste de instalação em máquina limpa

Teste feito em 2026-10-30, no notebook do Silvestre (Windows), sem nada instalado antes. Este arquivo alimenta o prompt de instalação e o guia do cliente. Só entra aqui o que foi visto no teste.

## 1. O terminal não reconhece o `docker` logo após instalar o Docker Desktop

**O que aconteceu:** depois de instalar o Docker Desktop, o terminal do VS Code não reconheceu o comando `docker`. Só passou a funcionar depois de fechar o VS Code por completo e abrir de novo.

**O que o kit deve fazer:**
- Depois de instalar o Docker Desktop, o prompt avisa a pessoa, antes de qualquer outro passo, que ela precisa fechar o VS Code (ou o terminal da ferramenta de IA) por completo e abrir de novo.
- O aviso diz o porquê em linguagem simples: o programa novo só aparece para o terminal quando ele é aberto de novo.
- O prompt deve ser retomável: ao voltar, a IA confere se o `docker` responde antes de seguir, em vez de assumir que deu certo.
- O guia do cliente repete esse aviso, com a frase "fechar por completo" explicada (não basta fechar a janela do terminal).

## 2. O primeiro download do motor demora cerca de 2 minutos

**O que aconteceu:** na primeira vez, baixar o motor levou cerca de 2 minutos.

**O que o kit deve fazer:**
- Avisar antes de começar que a primeira vez demora uns 2 minutos e que isso é normal.
- Pedir para a pessoa não fechar a janela nem repetir o comando enquanto espera.
- Dizer que nas próximas vezes é bem mais rápido, só se isso for confirmado em teste. Até lá, não afirmar.
- Mostrar sinal de progresso quando possível, para não parecer travado.

## 3. JSON com aspas escapadas no terminal falha em algumas versões do PowerShell

**O que aconteceu:** o `curl` com o JSON do pedido escrito entre aspas escapadas falhou em algumas versões do PowerShell.

**O que o kit deve fazer:**
- Nunca falar com o motor passando JSON escapado na linha de comando.
- Falar com o motor sempre por Python (biblioteca padrão) ou por arquivo de pedido (o JSON fica salvo em um arquivo e o programa lê o arquivo).
- Nenhum passo do prompt de instalação nem do guia pode pedir para a pessoa digitar ou colar um `curl` com JSON.
- Os testes automatizados cobrem a montagem do pedido em Python, sem rede.

## 4. O Silvestre não conhecia Docker

**O que aconteceu:** o dono do kit nunca tinha usado Docker. O comprador típico também não vai conhecer.

**O que o kit deve fazer:**
- Antes de cada passo, o prompt explica em uma ou duas frases o que vai acontecer e por que, sem jargão.
- Explicar o que é o Docker na primeira vez que aparece, por exemplo: "um programa que roda a ferramenta de busca isolada do resto do seu computador, como se fosse uma caixa fechada".
- Termos como imagem, contêiner e porta só aparecem se forem indispensáveis, e sempre com uma explicação curta.
- Continuar pedindo confirmação antes de cada passo que muda o computador, como manda o CLAUDE.md.
- Dizer o que a pessoa vai ver na tela em cada passo e o que fazer se for diferente.

## Onde aplicar

- Prompt de instalação: itens 1, 2, 3 e 4.
- Guia do cliente: itens 1, 2 e 4.
- Código do kit (comunicação com o motor): item 3.
