# Arquitetura do Lead Kit Silver

Documento de planejamento. Descreve como o kit é organizado e em que ordem construir. A entrevista e o formato do perfil estão em `entrevista-e-perfil.md`.

## Visão geral e princípios

O Lead Kit Silver é um prompt de instalação mais um conjunto de arquivos. A IA do comprador (Claude Code, Codex e similares) instala o kit no computador dele, entrevista o dono do negócio e abre um painel local que busca negócios no Google Maps, dá nota a cada lead e prepara a mensagem de abordagem.

O que o comprador recebe:

- Um prompt de instalação que ele cola na própria IA.
- O repositório do kit: servidor local, painel, validador, modelos e a skill de qualificação.
- Um guia curto de uso e de abordagem responsável, em português.

Princípios que valem pra todas as decisões abaixo:

1. **Tudo roda no computador da pessoa.** Nenhum lead sai da máquina. O kit não tem servidor nosso, conta, login nem custo recorrente.
2. **IA só na instalação e na entrevista.** Depois disso o painel funciona sem chamar IA. Nota e mensagem saem de regras e modelos salvos, sempre com o mesmo resultado.
3. **Poucas dependências, e a instalação cuida delas.** Python 3.10+ com biblioteca padrão, painel em HTML e JavaScript puros, sem build e sem npm. O que faltar no computador (Python e Docker) o prompt instala, depois de listar e pedir confirmação.
4. **Honestidade primeiro.** O kit diz o que raspa, o risco com os termos do Google, a LGPD e o limite do WhatsApp. Só prometemos o que foi testado.
5. **Crédito e licença intactos.** O motor `gosom/google-maps-scraper` (MIT) roda sem alteração, com versão fixada, e o `CREDITS.md` e o `LICENSE` ficam no kit.
6. **Funciona em qualquer sistema, com Windows como o testado.** Todo comando tem caminho pra Windows, macOS e Linux, mas o material de venda só cita o que o Silvestre testou.

## Estrutura do repositório

O repositório é o pacote que o comprador baixa. Tudo que é código fica em `kit/`, tudo que é dado da pessoa fica em `dados/` e fora do controle de versão. Nomes de arquivo em português, sem acento, pra evitar problema no Windows.

```text
lead-kit-silver/
  README.md                 visão rápida e como começar
  LICENSE                   MIT do kit original
  CREDITS.md                créditos do motor e do kit base (obrigatório)
  docker-compose.yml        motor em Docker, só em 127.0.0.1 (caminho principal da v1)
  iniciar.bat               sobe motor e painel com um clique (Windows)
  iniciar.sh                o mesmo no macOS e Linux
  AGENTS.md                 regras para Codex e outras IAs
  CLAUDE.md                 regras para o Claude Code
  .claude/skills/lead-kit/  skill de qualificação e abordagem
  entrevista/
    perguntas.md            as 12 perguntas, na ordem
    esquema.json            formato e limites do perfil
    perfil.exemplo.json     exemplo preenchido
  kit/
    servidor.py             servidor local e rotas da API
    testar_api.py           testa a API pelo terminal, só com Python (sem curl)
    consulta.py             filtros, resumo, detalhe e exportação CSV dos leads
    buscar.py               comando de terminal: faz uma busca e lista leads com nota
    motor.py                cliente do motor (jobs, status, download)
    geocodificar.py         cidade para latitude e longitude (Nominatim)
    limpeza.py              lê o CSV do motor, limpa os campos e tira duplicados
    diagnostico.py          descobre por que o motor não responde (Docker ausente, Docker parado ou só o motor parado)
    ligar_motor.py          liga o motor em segundo plano a pedido do painel (comando fixo, log em dados/)
    grade.py                pontos de uma busca maior (centro e quatro pontos ao redor)
    xlsx.py                 gera planilha .xlsx só com zipfile e XML escritos à mão
    pontuacao.py            regras e nota A, B, C
    regras.json             tabela de regras e pesos padrão
    modelos.py              troca dos marcadores nas mensagens (adiantado na fase 2, com modelo provisório)
    validar_perfil.py       valida o perfil.json
    banco.py                SQLite dos leads e do status
    painel/
      index.html            casca da página (o servidor escreve o token aqui)
      estilo.css            tokens de cor, tema claro e escuro, componentes
      favicon.svg
      tema.js               aplica o tema salvo antes de a página aparecer
      api.js                fala com o servidor (token, erros, só a última resposta vale)
      util.js               funções puras: query, abas, tema, tipos de falha
      dom.js                monta elementos sem innerHTML; avisos, comandos, botões
      app.js                casca: abas, estado do motor e do perfil, avisos, troca de tela
      tela-perfil.js        perfil ausente ou com problemas
      tela-buscar.js
      tela-leads.js         tabela, filtros, carregamento por partes, gaveta do lead, exportação
      tela-oferta.js
  testes/
    fixtures.py             leads e perfil fictícios, em Python (o .gitignore bloqueia CSV)
    perfis/                 três perfis de teste
    test_banco.py
    test_buscar.py
    test_consulta.py
    test_geocodificar.py
    test_grade.py
    test_limpeza.py
    test_modelos.py
    test_motor.py
    test_pontuacao.py
    test_validacao.py
    test_painel.py          confere o painel por texto: rotas usadas, nada de innerHTML, sem URL externa, sem travessão
    test_painel_js.py       roda js/util.test.mjs com o Node, se ele existir (só ferramenta de desenvolvimento)
    js/util.test.mjs        testes de util.js e api.js
    js/leads.test.mjs       prova que dado malicioso do Google vira só texto na tela de Leads (DOM de mentira)
    js/buscar.test.mjs      tela Buscar: textos, resumo, erros, zero resultado, sem botão de cancelar
    js/oferta.test.mjs      tela Minha oferta: rascunho, conferência, limpeza, cortes e prévia das mensagens
    js/ligar-motor.test.mjs botão Ligar o motor
    js/dom_falso.mjs        o DOM de mentira usado pelos testes de JavaScript
    test_demo.py            a demonstração do painel sobe em todos os estados
    demo_painel.py          servidor de demonstração com dados fictícios, um modo por estado do painel (ver o topo do arquivo)
    test_servidor.py
    test_xlsx.py
    test_oferta.py          cortes do painel iguais aos do kit, descrições, pesos padrão intocados
    test_diagnostico.py
    test_privacidade.py     o que a tela diz que sai do computador bate com o que o código faz
    test_testar_api.py
  docs/
    planejamento/           este documento e entrevista-e-perfil.md
    guia-de-uso.md
    abordagem-responsavel.md
  dados/                    criado na instalação, no .gitignore
    perfil.json
    leads.db
    instalacao.json         progresso da instalação (pausar e retomar)
    exportacoes/
  ferramentas/              Python portátil, se usado; baixado na instalação, no .gitignore
```

Regras da estrutura:

- O que a pessoa pode editar sem medo: `dados/perfil.json` e as mensagens dentro dele.
- `kit/regras.json` é o único lugar com os pesos padrão, então mudar uma regra nunca exige mexer em código.
- `CLAUDE.md` e `AGENTS.md` dizem o mesmo, em dois arquivos, porque cada ferramenta lê o seu.

## Componentes

O kit tem seis peças locais. O servidor local é o centro: o painel só fala com ele, e só ele fala com o motor, com o serviço de geocodificação e com os arquivos em `dados/`.

```text
Computador do comprador
  Painel (navegador) --> Servidor local --> Motor de busca (porta 8080) --> Google Maps (internet)
                              |
                              +--> Dados locais (perfil.json, leads.db)
                              +--> Nominatim (internet): cidade vira coordenada
  IA do comprador (só na instalação) --> Dados locais (grava o perfil)
```

A IA do comprador só escreve o perfil, na instalação. Depois disso o painel funciona sem ela. Só o motor e a geocodificação falam com a internet.

| Peça | Tecnologia | Por quê |
| --- | --- | --- |
| Motor | `gosom/google-maps-scraper` v1.18.1, em Docker (imagem oficial) | Já faz a busca, licença MIT, versão fixada |
| Servidor local | Python 3.10+ só com a biblioteca padrão (Python portátil se o computador não tiver) | Nada de pacote pra instalar, e o kit base já usa Python |
| Painel | HTML, CSS e JavaScript puros | Sem build, abre em qualquer navegador |
| Banco | SQLite em `dados/leads.db` | Um arquivo só, já vem com o Python |
| Perfil | JSON validado por script | Legível, editável e fácil de testar |
| Instruções pra IA | `CLAUDE.md`, `AGENTS.md` e `SKILL.md` | Funciona no Claude Code, no Codex e em ferramentas parecidas |

## Fluxo de instalação

O comprador abre a IA dele numa pasta vazia e cola o prompt de instalação. O prompt é curto e só orquestra: os arquivos do kit já vêm prontos e testados, a IA não escreve o código do zero. Isso deixa a instalação repetível e fácil de testar.

1. **Apresentação e consentimento.** A IA explica o que o kit faz, lista tudo o que vai instalar ou baixar e pede um "pode seguir" antes de cada passo que muda o computador.
2. **Pré-checagem e instalação do que falta.** Sistema, Python, motor, Docker e portas livres (tabela abaixo). O que faltar, a IA instala depois de listar e pedir o "pode seguir". Nada é instalado às escondidas.
3. **Arquivos do kit.** A pessoa baixa o `.zip` pela área de membros da Kiwify e extrai na pasta. A IA confere se `LICENSE`, `CREDITS.md` e `kit/` estão lá.
4. **Motor.** Sobe o motor em Docker com `docker compose up -d`, na imagem de versão fixada. Termina com uma checagem em `http://127.0.0.1:8080/api/v1/jobs`. O download da imagem é o maior da instalação e entra na lista de confirmação.
5. **Entrevista.** As 12 perguntas, o resumo e o "confirmo", gerando `dados/perfil.json` (ver `entrevista-e-perfil.md`).
6. **Validação.** `python kit/validar_perfil.py`. Se falhar, a IA refaz só a pergunta com problema.
7. **Teste de ponta a ponta.** Uma busca pequena (uma categoria, uma cidade, poucos resultados) pra provar que motor, nota e mensagem funcionam no computador dessa pessoa.
8. **Painel.** `python kit/servidor.py` e o endereço `http://127.0.0.1:8787`. A IA abre o navegador e mostra o primeiro lead com nota e mensagem.
9. **Atalho do dia a dia.** Um `iniciar.bat` (Windows) e um `iniciar.sh` (macOS e Linux) sobem motor e painel com um clique, sem precisar da IA.

Pré-checagem do passo 2:

| Item | Como confere | Se faltar |
| --- | --- | --- |
| Sistema | `platform.system()` no Python | Escolhe os comandos de Windows, macOS ou Linux |
| Python 3.10 ou mais novo | `python --version`, ou `py -3 --version` no Windows | Instala pelo `winget` (Windows), Homebrew (macOS) ou gerenciador do sistema (Linux), ou usa o Python portátil da pasta `ferramentas/` |
| Docker rodando | `docker info` | Instala o Docker Desktop pelo `winget`, avisa que vai pedir permissão e reinício, e usa o pausar e retomar |
| Portas 8080 e 8787 livres | Tenta abrir a porta | Pergunta se pode usar outra porta e grava no perfil |
| Internet | Acessa a imagem do motor e o Nominatim | Explica que a busca precisa de conexão |
| Pasta com permissão de escrita | Cria e apaga um arquivo de teste | Pede pra escolher outra pasta |

Regras do prompt:

- Nunca pede pra desligar antivírus, firewall ou as permissões de segurança da ferramenta de IA.
- Cada falha tem uma mensagem em português dizendo o que aconteceu e o que fazer. A IA não tenta três gambiarras seguidas.
- Se nenhum caminho do motor for possível na máquina, o prompt para e explica o motivo, em vez de improvisar outro caminho.
- O prompt nunca promete "sem nenhum problema". Ele promete que, se algo travar, diz o que aconteceu e como continuar.

Pausar e retomar. Alguns passos nenhum prompt faz sozinho: aceitar a janela de permissão do Windows (UAC), reiniciar o computador, ligar a virtualização na BIOS e aceitar os termos do Docker Desktop. Por isso a instalação é retomável:

- A cada passo concluído, a IA grava o progresso em `dados/instalacao.json`.
- Quando precisa de uma ação do cliente, para com uma mensagem curta, por exemplo: "Reinicie o computador, abra a IA nesta mesma pasta e cole o prompt de novo. Eu continuo de onde parei."
- Ao colar o prompt de novo, a IA lê esse arquivo, confere o que já está pronto e segue do próximo passo, sem refazer a entrevista.
- Se a virtualização estiver desligada na BIOS, a IA explica em linguagem simples como ligar e avisa que depende do modelo do computador. É o caso que mais pode travar na instalação.

## API do servidor local

O servidor (`kit/servidor.py`) usa só a biblioteca padrão do Python, escuta em `127.0.0.1:8787`, serve o painel e responde em JSON. Ele é o único que fala com o motor em `127.0.0.1:8080`: o navegador nunca chama o motor direto.

| Rota | Pra quê |
| --- | --- |
| `GET /api/estado` | Motor no ar, perfil válido, versão do kit, busca em andamento e, quando o motor não responde, o motivo (`motor_diagnostico`: Docker ausente, Docker parado ou só o motor parado) |
| `GET /api/opcoes` | Regras com pesos padrão, exclusões, marcadores, tamanhos de busca, UFs e status. O painel monta os formulários com isso, sem repetir a lista no JavaScript |
| `GET /api/perfil` | Lê o perfil |
| `PUT /api/perfil` | Grava o perfil, mas só depois de passar no validador |
| `POST /api/motor/ligar` | Liga o motor (`docker compose up -d`) em segundo plano. Exige token. Só roda com o Docker ligado e o motor desligado (senão `409`). Responde `202` na hora; o painel acompanha por `ligando_motor` em `GET /api/estado` (`ligando`, `ok` ou `erro`, com mensagem simples). Comando fixo, sem shell, caminho absoluto do `docker-compose.yml`, pasta do kit, sem janela de console no Windows, limite de 10 minutos. A saída vai para `dados/log-motor.txt`, que nenhuma rota entrega |
| `POST /api/buscas` | Cria uma busca: categoria, cidade e UF, tamanho, extras |
| `GET /api/buscas` | Lista as buscas já feitas |
| `GET /api/buscas/{id}` | Status e progresso de uma busca: etapa, ponto atual e total de pontos, tempo decorrido, tempo estimado e, ao fim, `total_leads`, `novos`, `ja_existiam`, `fora_da_lista`, `terminou_em` e, se deu erro, `erro` e `erro_tipo` (`cidade`, `servico_de_mapas`, `motor`, `formato`, `parcial`, `interrompida` ou `inesperado`). **Não existe rota para cancelar uma busca** (ver `fase0-verificacao-motor.md`) |
| `GET /api/leads` | Lista com filtros: busca, nota, status, texto, excluídos, `sem_site=1` e `celular=1`. Devolve também `contagem_por_letra` (com todos os filtros menos o da letra, para os botões A, B e C) |
| `GET /api/leads/{id}` | Um lead com motivos da nota e mensagem já preenchida |
| `PATCH /api/leads/{id}` | Muda status, anotação ou a mensagem editada |
| `POST /api/leads/reavaliar` | Recalcula as notas depois que o perfil mudou |
| `GET /api/exportar` | Baixa os leads filtrados. `?formato=csv` (padrão) ou `?formato=xlsx`. **Exige o cabeçalho `X-Token`**, como as escritas, porque entrega os dados dos leads em arquivo |

Só uma busca roda por vez (`409` se já houver outra, com o id dela). O estado vem do servidor, então recarregar a página continua mostrando a busca em andamento.

Fluxo de uma busca: o painel envia `POST /api/buscas`, o servidor geocodifica a cidade (Nominatim), cria o job no motor, acompanha o status em segundo plano, baixa o CSV quando termina, limpa e pontua cada linha e grava no SQLite. O painel só consulta o progresso.

Armazenamento em `dados/leads.db` (SQLite):

- **buscas:** id, data, parâmetros, status, id do job no motor.
- **leads:** dados do Maps, nota, letra, motivos, status (novo, contatado, respondeu, fechado, descartado), anotação, mensagem editada.
- **Duplicados:** o mesmo negócio em buscas diferentes vira um lead só. A chave é o identificador do Maps se o CSV trouxer um, senão o nome mais o endereço normalizados. Colunas conferidas na fase 0 com um CSV real (36 colunas, lista em `fase0-verificacao-motor.md`). `place_id` e `cid` vieram preenchidos em todas as linhas e servem de chave contra duplicados. `order_online` e `reservations` chegam como JSON, não como texto simples. `emails` só vem preenchido quando o job usa a opção de e-mail (`email: true`), e isso deixa a busca mais lenta. Na API do motor o campo `lang` usa código de duas letras (`pt`), e `pt-BR` é recusado.
- A exportação tem dois formatos, os dois só com a biblioteca padrão do Python:
  - **CSV** em UTF-8 com BOM, pra abrir certo no Excel.
  - **.xlsx** feito à mão com `zipfile` e XML (`kit/xlsx.py`), pensado como relatório pronto pra mostrar a um cliente. Colunas em português: Negócio, Nota, Pontos, Motivos, Categoria, Telefone, WhatsApp, Site, Endereço, Avaliação no Maps, Nº de avaliações, Status, Anotação e Mensagem (mais "Excluído por" só quando há excluídos). Cabeçalho em destaque, largura de coluna ajustada, primeira linha congelada, filtro ligado, cor na letra da nota (A verde, B amarelo, C cinza), impressão em paisagem com o cabeçalho repetido. Todo texto é gravado como texto puro, nunca como fórmula. O link `wa.me` (com a mensagem já preenchida) só existe para telefone que parece celular, e o site só vira link se for `http` ou `https`.

Segurança do servidor local, porque uma página qualquer da internet pode tentar falar com `127.0.0.1`:

- Aceita só requisições com `Host` igual a `127.0.0.1:<porta>` ou `localhost:<porta>`. Qualquer outro valor, ou a falta do cabeçalho, recebe 403, inclusive em leitura.
- Gera um token a cada início e o escreve dentro do `index.html` ao servir `/` (marcador `{{TOKEN}}`). Nunca aparece em rota de dados nem em mensagem de erro. Toda rota que altera algo exige o cabeçalho `X-Token` (401 sem ele).
- Não libera CORS pra nenhuma origem: nenhuma resposta tem cabeçalho `Access-Control-*` e `OPTIONS` é recusado.
- Recusa `Origin` de outro site, mesmo com token válido.
- Escrita só com `Content-Type: application/json` (415) e corpo de até 1 MB (413).
- Só escuta em `127.0.0.1` e não reaproveita porta já ocupada (no Windows isso deixaria outro programa pegar a mesma porta).
- Só serve arquivos de dentro de `kit/painel/`, com extensões do painel. Tentativas de sair da pasta recebem 404.
- Não lê nem grava nada fora da pasta do kit.
- Uma conexão SQLite por thread: cada requisição e a thread da busca abrem e fecham a sua. Só uma busca por vez (409 se houver outra).
- Na exportação CSV, texto que começa com `=`, `+`, `-`, `@`, tabulação ou retorno ganha um apóstrofo, para a planilha não executar como fórmula. Telefone brasileiro sai como `(DD) NNNNN-NNNN`, sem o `+55`.
- Lead tem `id` inteiro na API. "Possível rede" e a exclusão são calculadas na hora e nunca gravadas no lead.

## Painel

O painel é uma página estática (`index.html`, `estilo.css` e alguns arquivos `.js` pequenos) sem framework e sem build. Ela só conversa com a API da seção anterior. A referência visual é o preview já aprovado na direção (prata e grafite, minimalista, tema claro e escuro); o refinamento do design fica pra depois, sem mexer na API.

| Tela | O que faz | Dados |
| --- | --- | --- |
| Buscar | Tipo de negócio (sugestões do perfil, aceita texto livre), UF e cidade (sugestões das regiões do perfil), tamanho da busca (rápida e média; ampla aparece como "em breve" e desativada) e o extra de e-mail. Cobertura fixa em 10 km ao redor do centro da cidade. Mostra a busca em andamento com progresso real, o resumo ao fim, os erros e o histórico | `GET /api/opcoes`, `GET /api/perfil`, `GET /api/buscas`, `POST /api/buscas`, `GET /api/buscas/{id}` |
| Leads | Tabela com nota A, B, C, filtros (nota, status, texto, lista ou excluídos, busca), carregamento por partes de 100 e exportação. Ao abrir um lead (gaveta): "Por quê" em frases simples com os pontos, mensagem pronta e editável, copiar, abrir o WhatsApp, status e anotação. Fica sempre visível o aviso de conformidade quando a área é regulada ou a pessoa não sabe | `GET /api/leads`, `GET` e `PATCH /api/leads/{id}`, `GET /api/exportar` (CSV e .xlsx, com token), `GET /api/perfil`, `GET /api/buscas` |
| Minha oferta | Edita o perfil, com as mesmas respostas das 12 perguntas: o que vende, nome e empresa, tipos de negócio, regiões, porte, atendimento, melhor cliente, regras de nota com peso de 0 a 5, cortes A e B (automáticos ou manuais), o que evitar (com listas de concorrentes e categorias), canais, tom, oferta de entrada, volume por semana, mensagens por canal e a resposta sobre regras da área. Salvar grava o perfil e dá nota de novo aos leads | `GET /api/opcoes`, `GET` e `PUT /api/perfil`, `POST /api/leads/reavaliar` |

Visual do painel (direção A, "Instrumento", etapa 1 do redesign):

- **Prata e grafite**, claro e escuro. **Menu lateral** no computador e **barra no topo** no celular (sem rolagem lateral). Sem selo nem sigla: só o nome em texto, que vem de `kit/produto.py` (o nome do produto ainda é decisão em aberto) e é trocado no `index.html` pelo servidor.
- **Fontes só do kit:** IBM Plex Sans e IBM Plex Mono em woff2, em `kit/painel/fontes/`, com a licença OFL sem alteração. Nenhum pedido a serviço de fonte.
- **Leitura fácil para leigos:** corpo em 16 px, nada abaixo de 13 px, alvos de clique de 44 px, fonte de números só em números e comandos (nunca em rótulos nem em maiúsculas). Um teste confere cada uma dessas regras no CSS.
- **A nota** é uma letra grande dentro de uma forma: A círculo verde, B quadrado âmbar e C losango azul-acinzentado (C é prioridade menor, não "lead ruim", então não usa vermelho), com os pontos ao lado. Quem está fora da lista não ganha letra nem cor. A tabela e a gaveta usam só o termo "Nota", e a nota do Google aparece como "Avaliação no Google: 4,8 (312 avaliações)".
- **Tela Buscar:** três passos numerados (tipo de negócio, cidade, tempo de espera), o botão "Buscar leads" logo abaixo dos passos e os avisos de privacidade e uso responsável depois dele. O resultado da última busca e o histórico ficam abaixo do formulário, então o botão fica perto dos campos também depois de uma busca.
- **Nota A e B:** A é círculo cheio e B é quadrado só de contorno, então a diferença não depende só da cor (C é losango suave, em azul acinzentado).
- **Nas telas, "motor" vira "buscador"** (Buscador ligado, Ligar o buscador). Código, testes e documentação técnica continuam com "motor".
- **Menu pelo teclado:** setas para cima e para baixo (e esquerda e direita) trocam de aba.

Regras da tela Buscar (fase 3):

- **Uma busca por vez, mostrada com clareza.** Se já existe uma busca (iniciada por esta página, por outra aba ou antes de recarregar), a tela mostra só ela: título, tamanho, tempo decorrido, ponto atual, etapa e a barra, tudo lido do servidor a cada 2 s. Busca de um ponto só tem barra sem fim definido, em vez de um número inventado.
- **Sem botão de cancelar.** Nem o servidor nem o motor têm cancelamento (testado). A tela diz que a busca termina sozinha e que continua se a página for recarregada, desde que a janela do kit fique aberta.
- **Sem promessa de quantidade.** A tela diz que o Google varia entre buscas e que o resultado depende da cidade e do tipo de negócio. Os tempos são sempre "estimativa" (rápida: cerca de 1 minuto; média: cerca de 5 a 6 minutos). Os números medidos na fase 0 e na fase 3 ficam só na documentação interna.
- **Resumo honesto ao fim:** quantos negócios foram encontrados, quantos são novos, quantos já existiam de buscas anteriores e quantos ficaram fora da lista pelas exclusões do perfil. **Resultado zero nunca aparece como sucesso**: a tela explica que pode ser a cidade, o termo ou uma mudança no Google, e o que tentar (inclusive procurar uma versão mais nova do kit, que é o caminho de manutenção contra mudanças do Google).
- **Erros com mensagem própria:** motor desligado, Docker parado, Docker não encontrado, cidade não encontrada, serviço de localização inacessível, falha no meio da busca (o que já chegou fica salvo e aparece em Leads), formato de resultado desconhecido, busca interrompida por o kit ter sido fechado, e campo vazio (validado antes de enviar, sem pedido ao servidor).
- **O que sai do computador:** a tela diz, e um teste confere com o código, que só o nome da cidade e o estado vão para o serviço de localização OpenStreetMap (Nominatim), que o motor local consulta o Google Maps pela conexão da pessoa e que leads, notas, perfil e mensagens ficam só no computador.
- **Uso responsável:** aviso curto sobre os termos do Google, a LGPD e o envio manual. Na primeira busca maior, um aviso (que não bloqueia) sobre o risco de o Google limitar o acesso da internet por um tempo.

Regras da tela Minha oferta (fase 3):

- **Só edita o que as 12 perguntas já cobrem.** Nenhuma pergunta nova e nenhuma mudança nas perguntas. Os pesos padrão e os cortes de 70% e 40% não foram mexidos (um teste confere).
- **Nada de IA.** A tela é um formulário. Salvar envia o perfil inteiro por `PUT /api/perfil` (o servidor valida e guarda a cópia anterior em `perfil.anterior.json`) e depois chama `POST /api/leads/reavaliar`. O resultado aparece em frase: quantos leads, e quantos A, B e C.
- **Tudo vem do servidor.** Regras, exclusões (com uma `descricao` em português simples), marcadores, canais, tons, portes, atendimentos, volumes por semana, modelos padrão e frases de motivo chegam por `GET /api/opcoes`, sem lista repetida no JavaScript.
- **Cortes:** por padrão o painel calcula (70% e 40% da soma dos pesos, para cima, a mesma conta de `pontuacao.cortes`, conferida por teste nos dois lados) e mostra a frase "Nota A: 7 ou mais...". Quem quiser pode digitar os dois cortes.
- **Mensagens:** uma por canal (WhatsApp e e-mail), com botões que incluem os marcadores e uma prévia com um negócio de exemplo. Vazio quer dizer "usar o modelo padrão". O servidor exige a saída clara ("é só avisar que não escrevo mais") e mostra o erro em português.
- **Não perde o que a pessoa fez:** o que foi editado e não foi salvo continua ao trocar de aba (enquanto a página estiver aberta), a página avisa antes de fechar com mudanças e há "Descartar mudanças". Erros aparecem no campo e num resumo no topo, e nada é enviado se faltar campo obrigatório.
- **Perfil com problemas:** a tela abre mesmo assim, mostra o que o servidor achou e deixa corrigir.
- **Cinco etapas, todas clicáveis a qualquer momento** (Sobre você, Quem atender, O que importa, O que evitar, Como falar), com Voltar e Continuar. Tudo que a pessoa digita fica na página ao trocar de etapa, e salvar vale de qualquer etapa. Erros aparecem no campo, num resumo no alto (com "Ver na etapa N") e com um "!" na etapa. O link "Corrigir em Minha oferta" da tela de perfil inválido leva à etapa do primeiro problema (`etapaDoErro`, testado).
- **Quanto importa cada coisa:** Ignorar = 0, Pouco = 1, Importa = 2, Muito = 3. O esquema continua aceitando 0 a 5: peso 4 ou 5 aparece como "Personalizado: N" e não se perde. Regra ausente do perfil e regra com peso 0 dão exatamente as mesmas notas e cortes (`testes/test_pesos_ignorar.py`), então ausente aparece como "Ignorar". Só a regra que a pessoa mexe é regravada, e a ordem das regras do perfil é mantida (no empate de pontos vale a ordem do perfil).
- **Barra de salvar:** uma linha só, "Salvar e dar nota de novo" como botão principal e "Descartar mudanças" pequeno. Só aparece com mudança pendente. "Tudo salvo" é uma frase temporária (8 s). No celular a barra se desloca para fora da tela ao rolar para baixo e volta ao rolar para cima (nunca `display: none`), reaparece quando um botão dela recebe foco e fica à vista se há erro. Há um botão de salvar também no fim da última etapa. O aviso do navegador sobre sair com mudanças não salvas continua valendo.
- **Salvar durante uma busca:** o servidor recusa (`409`, com o id da busca) o `PUT /api/perfil` e o `POST /api/leads/reavaliar` enquanto houver busca em andamento, e a tela mostra "Tem uma busca em andamento. Espere ela terminar para salvar o perfil...". Motivo: a busca usa o perfil de quando começou, e trocar no meio deixaria leads da mesma busca com notas de regras diferentes. Esperar é o jeito mais simples e seguro. Há teste: nada é gravado durante a busca e, depois dela, salvar funciona.
- **Tempo de recalcular:** medido com 5000 leads fictícios, `POST /api/leads/reavaliar` levou cerca de 0,2 s e `PUT /api/perfil` cerca de 0,01 s (Windows, Python 3.13). Como é bem menos que 2 s, a tela só mostra "Salvando e dando nota de novo..." na barra de baixo, sem tela de espera à parte.
- **Pesos e cortes são provisórios.** Os pesos padrão de `regras.json` (sem_site 3, so_instagram 2, nota_alta 2, nota_baixa 2, muitas_avaliacoes 1, poucas_avaliacoes 1, celular 2, delivery 1, reserva 1, sem_email 1) e os cortes de 70% e 40% ficam como estão até a fase 5, que valida com 3 perfis de teste.
- **Acessibilidade com leitor de tela NÃO foi testada.** O painel usa rótulos, `role` e avisos para leitor de tela, mas ninguém abriu a tela com NVDA, Narrador ou outro. Enquanto esse teste não for feito, **nenhum texto de venda, guia ou página pode afirmar que o painel é acessível.** O que existe é só marcação feita com cuidado.

Regras da tela de Leads (fase 3):

- **Dados do Google não são confiáveis.** Nome, categoria, endereço, site, telefone e e-mails entram na página só como texto (`el()` cria nós de texto, nunca `innerHTML`), e `el()` recusa atributo de evento em texto e `href`/`src` com `javascript:`, `data:` ou `vbscript:`. O site e o link do Maps só viram link se forem `http` ou `https`. Há teste com o nome `<img src=x onerror=alert(1)>`.
- **WhatsApp:** o servidor entrega `whatsapp_numero` (`55` + DDD + celular, só dígitos, ou nulo), e o painel confere o formato de novo antes de montar `https://wa.me/<número>?text=<mensagem codificada>`. Só existe para telefone que parece celular (estimativa). A mensagem vem pronta de `modelos.py`, preenchida com os dados do lead. O link abre em outra aba, com `rel="noopener noreferrer"`. **O envio é sempre manual, um lead por vez: não há botão de envio em massa nem "copiar todos os números".**
- **Uma mensagem editada por lead:** a edição vale para todos os canais, fica salva sozinha (depois de 800 ms parado, ao sair do campo e ao fechar a gaveta) e dá para voltar ao modelo.
- **Lista grande:** o painel pede 100 leads por vez (`limite` e `offset`) e tem o botão "Mostrar mais N". A ordem é estável entre as partes (nota, nome, chave), e a contagem por letra vem da mesma consulta. Testado com 650 leads fictícios, no servidor e no navegador.
- **Estados com mensagem própria:** carregando, nenhuma busca ainda (só o convite para buscar), todos fora da lista pelas exclusões, filtro sem resultado, erro ao carregar, falha de rede ao marcar status (o status volta ao que estava e a gaveta mostra o erro) e falha ao salvar edição (o texto continua na tela).
- **Filtros rápidos "Sem site" e "Com celular":** usam as mesmas funções das regras de nota (`pontuacao.criterio_sem_site` e `pontuacao.criterio_celular`), então o filtro e a nota nunca discordam. Valem mesmo se a regra estiver desligada no perfil, entram na contagem por letra e na exportação.
- **Exportação:** o painel baixa por `fetch` com o token e entrega o arquivo como `Blob`. Os botões ficam desligados quando não há leads na tela.

Comportamentos que valem desde a v1:

- Se o perfil não existe ou não é válido, o painel abre numa tela que explica como rodar a entrevista na IA, em vez de quebrar.
- Se o motor está desligado, mostra um aviso com o comando pra subir, e a aba Leads continua funcionando com o que já foi salvo.
- O aviso de conformidade da pergunta 12 fica fixo no topo da aba Leads quando aplicável.
- Abrir o WhatsApp usa o link `wa.me` com a mensagem preenchida. O envio é sempre manual, uma pessoa por vez. Sem disparo automático.
- O painel avisa uma vez, na primeira busca grande, sobre o risco de bloqueio temporário do IP.
- Respeita `prefers-reduced-motion` e funciona em tela de notebook e de celular.

## Fase 3: critérios de pronto, item por item

Conferidos em 2026-11-01, com a suíte automatizada (451 testes, sem rede), medições no navegador e prints em `prints/` (que não vai para o git). Legenda: **feito** (há teste, print ou medição), **parcial** (feito, mas falta algo dito na coluna), **não feito**.

| # | Critério | Estado | Evidência e ressalvas |
| --- | --- | --- | --- |
| 1 | As três telas (Buscar, Leads, Minha oferta), a partir do visual aprovado | **feito** | Visual "Instrumento" (direção A), aprovado em duas etapas. Prints `etapa1-*` e `etapa2-*`, claro e escuro, 1280 e 390 px |
| 2 | Uma busca real, feita só pelo navegador, termina com leads e mensagens na tela | **parcial** | Feito com o Google de verdade antes do redesign (busca rápida: 16 negócios; média: 65 e 88 em duas execuções, em `fase0-verificacao-motor.md`). **Não repetida com a versão final** (visual novo e "buscador"): falta uma busca rápida real de ponta a ponta |
| 3 | Estados de erro com mensagem própria (buscador desligado, Docker parado ou ausente, perfil ausente ou inválido, cidade não encontrada, falha no meio, resultado zero, busca interrompida, formato desconhecido) | **parcial** | 14 estados da demonstração × 2 telas × 2 tamanhos: sem erro de JavaScript, sem rolagem lateral e nenhuma letra abaixo de 13 px. Ressalvas: Docker parado e ausente só foram testados com a saída de `docker info` simulada (nunca com o Docker real parado); a faixa "o kit parou de responder" e a de "página desatualizada" (token) têm teste das funções, mas não foram vistas com o visual novo |
| 4 | Perfil ausente ou inválido abre numa tela que explica o que fazer, e o link leva à etapa do primeiro problema | **feito** | Prints de perfil ausente e inválido; link testado no navegador para a etapa 1 e para a etapa 5 (`perfil_invalido_mensagem`); mapeamento de mensagem para etapa testado em Node |
| 5 | Buscador desligado: aviso com o que fazer, e Leads continua funcionando | **feito** | Faixa e bloco com o botão "Ligar o buscador" e passo a passo recolhido (prints). O clique real ligou o motor de verdade com o Docker, antes de trocar "motor" por "buscador" nas telas |
| 6 | Leads: tabela, filtros, carregamento por partes, gaveta com a lista de pontos, status, anotação e exportação | **parcial** | Testes de JavaScript e do servidor; 650 leads no navegador; xlsx e CSV (excluídos no fim como "Fora da lista"); .xlsx aberto no Excel. **Google Planilhas não foi aberto** (sem acesso a uma conta aqui) |
| 7 | Mensagem pronta por lead e WhatsApp com envio sempre manual | **parcial** | Mensagem vem de modelos salvos (testes); o link `wa.me` é montado e testado; só abre com clique, um lead por vez, sem envio em massa. **Abrir o WhatsApp de verdade não foi testado** |
| 8 | Minha oferta: editar o perfil em cinco etapas e dar nota de novo | **feito** | Testes de Node e do servidor; navegador: etapas clicáveis, valores mantidos, salvar de qualquer etapa, erros, barra de salvar (computador e celular), pesos 4 e 5. Notas dos pesos padrão idênticas e salvar sem mexer não muda nenhum peso |
| 9 | Segurança do painel: sem `innerHTML`, `fetch` só em `api.js`, sem URL externa, sem travessão; dado do Google só vira texto | **feito** | `testes/test_painel.py`, `testes/js/leads.test.mjs` (nome malicioso), `testes/test_visual.py` |
| 10 | Servidor: Host, token e sem CORS, inclusive na rota de ligar o buscador | **feito** | `TestSeguranca` e `TestLigarMotor` em `testes/test_servidor.py` (a rota entra nas listas de segurança) |
| 11 | O que sai do computador é dito na tela e confere com o código | **feito** | `testes/test_privacidade.py`; só o nome da cidade e o estado vão ao Nominatim (OpenStreetMap), com limite de 1 pedido por segundo, cache e User-Agent |
| 12 | Nenhuma IA no painel | **feito** | Nota e mensagem saem de regras e modelos; nenhuma chamada externa no código do painel (teste de URLs) |
| 13 | Leitura fácil para leigos: corpo em 16 px, nada abaixo de 13 px, alvos de 44 px, números em fonte própria, contraste | **feito** | Testes do CSS e medições nos dois temas. Instruções "onde e como" em todas as telas. **Nenhuma pessoa leiga usou o painel**: a clareza para um iniciante real não foi testada |
| 14 | Celular (390 px) sem rolagem lateral | **feito** | Medido em 360, 390 e 1280 px nas três telas e nas cinco etapas de Minha oferta |
| 15 | Teclado: foco visível, gaveta presa e Esc devolve o foco | **feito** | Tab em todas as telas nos dois temas (contorno com contraste mínimo de 4,9) e gaveta |
| 16 | Leitor de tela | **não feito** | A marcação tem rótulos, grupos, avisos e `role`, mas ninguém abriu o painel com NVDA, Narrador ou outro. **Nenhum texto de venda, guia ou página pode afirmar acessibilidade** antes desse teste |
| 17 | Desempenho | **feito** | Dar nota de novo a 5000 leads: cerca de 0,2 s. Lista com 650 leads por partes de 100 |
| 18 | Tema claro e escuro | **feito** | Prints dos dois temas em todas as telas e etapas. As etapas 2 e 4 de Minha oferta em escuro foram vistas na rodada final (`etapa2-oferta-etapa{2,4}-escuro-*`) |
| 19 | Testes automatizados passam sem rede | **feito** | 451 testes (Python mais Node), rodados três vezes seguidas em 2026-11-01 |

Pendências que ficam para depois da fase 3:

1. Uma busca real rápida com a versão final (um minuto), pelo `iniciar` ou pelo painel.
2. Abrir a planilha de exemplo no Google Planilhas e o WhatsApp de verdade com uma mensagem.
3. Docker real parado e ausente (hoje só simulados), e a faixa de "kit parou" e de token vencido com o visual novo.
4. Teste com leitor de tela e com uma pessoa leiga.
5. A busca ampla continua "em breve": não medida, não definida.
6. Decisões em aberto da lista do `CLAUDE.md` (nome do produto, licença da camada paga, parcelamento no Kiwify, pesos padrão, perguntas da entrevista).

## Regras dos modelos de mensagem

Valem para a IA que escreve os modelos (fase 4), para o `perfil.json` e para o modelo provisório que o kit usa até lá. A lista completa de regras de escrita está em `entrevista-e-perfil.md`.

- **Sem artigo antes do nome do negócio.** O marcador `{nome}` leva o nome como o Google Maps entrega, e o gênero do negócio é desconhecido. Escreva "Vi que {nome} tem..." e nunca "Vi que a {nome} tem..." nem "o {nome}". Assim a frase fica certa para "Padaria Sol" e para "Império dos Pães".
- O mesmo vale para "da", "do", "na" e "no" antes de `{nome}` e `{categoria}`: reescreva a frase para não precisar deles.
- O `{motivo}` é uma frase neutra e comprovada pelo dado (ver `regras.json`), sem artigo nem gênero.

## Camada pública e camada paga

O motor e o kit base são abertos e qualquer pessoa pode baixá-los de graça. O que o comprador paga é a integração pronta, em português, com qualificação e abordagem: a entrevista, a nota, o painel, os modelos e o guia. Essa honestidade entra na página de venda.

| Camada | Conteúdo | Licença | Entrega |
| --- | --- | --- | --- |
| Pública | Motor `gosom/google-maps-scraper` na versão fixada | MIT, © Georgios Komninos | Imagem oficial do Docker, baixada na instalação |
| Pública | Partes aproveitadas do kit base de Mahan | MIT, © Mahan | Dentro do pacote, com `LICENSE` e `CREDITS.md` |
| Paga | Entrevista, perfil, validação, pontuação, modelos, painel, skill, guias e prompt | Licença própria do Lead Kit Silver | `.zip` e prompt na área de membros da Kiwify |

Sobre a licença da camada paga, a proposta é: o comprador pode usar, adaptar e construir produtos em cima do kit, inclusive pra clientes dele, mas não pode revender nem redistribuir o pacote como está. Isso casa com a ideia de a pessoa adaptar o código como quiser. O texto final da licença precisa de uma revisão antes da venda (ver riscos e decisões em aberto).

Atualizações:

- Cada versão nova do kit sai como um `.zip` novo, com changelog curto, na mesma área de membros.
- O campo `versao` do perfil deixa a atualização migrar perfis antigos sem refazer a entrevista.
- A versão do motor só muda depois de passar nos três perfis de teste.

## Plano de implementação em fases

Seis fases, cada uma terminando em algo que roda e que o Silvestre testa no Windows antes de seguir. Este documento e o da entrevista vão juntos pro repositório em `docs/planejamento/`, e o `CLAUDE.md` do repositório manda o Claude Code lê-los antes de qualquer código.

Regras fixas pro Claude Code durante toda a construção:

- Só biblioteca padrão do Python, painel sem framework e sem npm.
- Textos pra pessoa em português do Brasil, tom simples, sem travessões.
- Não inventar nomes de coluna do CSV nem parâmetros do motor: conferir na documentação do motor e com uma execução real.
- Cada fase com testes automatizados do que for lógica (nota, validação, modelos, rotas).
- Nunca pedir pra desligar segurança, nunca expor o servidor fora de `127.0.0.1`.
- Manter `LICENSE` e `CREDITS.md`. Parar e perguntar antes de qualquer decisão da lista de pontos em aberto.

| Fase | Entrega | Pronto quando |
| --- | --- | --- |
| 0. Base | Repositório, `LICENSE`, `CREDITS.md`, estudo do que reaproveitar do kit base e a verificação do motor em Docker, com o `docker-compose.yml` | O motor sobe no Windows do Silvestre em Docker, um job manual pela API devolve um CSV, e o resultado fica registrado em `docs/planejamento/fase0-verificacao-motor.md` |
| 1. Núcleo sem interface | `motor.py`, `geocodificar.py`, `banco.py`, limpeza do CSV, `pontuacao.py`, `regras.json`, `validar_perfil.py`, `esquema.json` | Um comando de terminal faz uma busca real e lista leads com nota e motivos, e os testes passam |
| 2. Servidor | `servidor.py` com todas as rotas e a segurança local (Host, token, sem CORS) | Testes das rotas passam e uma busca roda pela API do começo ao fim |
| 3. Painel | As três telas a partir do preview aprovado, com os estados de erro | Uma busca real, feita só pelo navegador, termina com leads e mensagens na tela |
| 4. Entrevista e instalação | `perguntas.md`, `CLAUDE.md`, `AGENTS.md`, skill, `modelos.py`, prompt de instalação com instalação automática do que falta e pausar e retomar | Instalação do zero numa pasta limpa, no Windows, com o Claude Code, sem ajuda manual, inclusive num computador sem Python nem Docker |
| 5. Pacote e testes de perfil | `.zip`, `iniciar.bat` e `iniciar.sh`, guias, os três perfis de teste, teste no Codex | Todos os critérios de aprovação do documento da entrevista cumpridos |

Depois da fase 5, fora do escopo da v1: refino do design do painel, motor como programa direto (sem Docker, ver `fase0-verificacao-motor.md`) e uma segunda versão do kit.

## Testes e critérios de pronto

O kit só vai pra venda quando passar nas três camadas abaixo. O que não foi testado não entra no material de venda.

| Camada | O que testa | Como |
| --- | --- | --- |
| Automatizada | Nota, validação do perfil, troca de marcadores, limpeza do CSV, rotas e segurança do servidor (Host errado e falta de token são recusados) | `python -m unittest` na pasta `testes/`, sem rede |
| Ponta a ponta | Busca real com o motor, do clique até o lead com mensagem | Manual no Windows, uma cidade pequena e uma categoria |
| Instalação | Prompt numa pasta limpa, sem ajuda | Claude Code primeiro, depois Codex, anotando cada tropeço |

Critérios de pronto da v1:

- Instalação do zero concluída sem o Silvestre digitar comando nenhum, mesmo que leve mais de uma sessão (por causa de reinício), e testada num computador sem Python nem Docker.
- Os três perfis de teste do documento da entrevista passam, com listas em ordem diferente pra a mesma busca.
- O painel abre e funciona sem a IA aberta, pelo `iniciar.bat`.
- Nenhuma rota responde a `Host` de fora nem a escrita sem token.
- `LICENSE` e `CREDITS.md` presentes no `.zip` final.
- A página de venda cita só sistemas e ferramentas testados.

## Riscos e decisões em aberto

| Tema | Risco ou dúvida | Proposta |
| --- | --- | --- |
| Entrega do código | A IA escrever tudo do zero seria frágil. Pacote pronto mais prompt é testável | Pacote `.zip` pronto e prompt que só orquestra (como está neste documento) |
| Docker | Exige WSL2, virtualização, permissão de administrador e reinício no Windows, e afasta iniciantes | Decidido em 2026-10-29: Docker é o caminho principal da v1, com instalação guiada. O programa direto falhou no Windows na fase 0 e vira pesquisa futura |
| Instalação automática | `winget`, permissões e BIOS podem falhar em alguns computadores | Pausar e retomar, mensagens claras e teste numa máquina sem Python nem Docker. Nunca prometer instalação sem nenhum problema |
| Termos do Google | Raspar o Maps viola os termos de uso do Google | Dizer isso claramente no guia e na página de venda |
| LGPD | Telefone e e-mail são dados pessoais | Guia de abordagem responsável e aviso fixo no painel |
| WhatsApp | Número pode ser banido por volume | Envio manual, volume baixo, sem disparo automático |
| Motor | Mudança de versão pode quebrar o CSV ou a API | Versão fixada e teste nos três perfis antes de atualizar |
| Licença paga | O texto de uso do comprador precisa ser claro | Revisão por alguém habilitado antes da venda |
| Preço | R$ 97 em 12x pode sair com juros pro cliente | Conferir as parcelas no Kiwify antes de anunciar |
| Nome | Disponibilidade de Lead Kit Silver | Checar no registro.br, Instagram e TikTok |
| Mentor | Produto parecido já existe na base do mentor | Conversar com ele sobre diferencial e uso do repositório aberto |
| Colunas do CSV | Nomes exatos podem diferir do que está no kit base | Conferir com um CSV real na fase 0 |
