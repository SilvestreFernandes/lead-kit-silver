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
    motor.py                cliente do motor (jobs, status, download)
    geocodificar.py         cidade para latitude e longitude (Nominatim)
    pontuacao.py            regras e nota A, B, C
    regras.json             tabela de regras e pesos padrão
    modelos.py              troca dos marcadores nas mensagens
    validar_perfil.py       valida o perfil.json
    banco.py                SQLite dos leads e do status
    painel/
      index.html
      app.js
      estilo.css
  testes/
    perfis/                 três perfis de teste
    test_pontuacao.py
    test_validacao.py
    test_servidor.py
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
| `GET /api/estado` | Motor no ar, perfil válido, versão do kit |
| `GET /api/perfil` | Lê o perfil |
| `PUT /api/perfil` | Grava o perfil, mas só depois de passar no validador |
| `POST /api/buscas` | Cria uma busca: categorias, cidade e UF, cobertura, tamanho, extras |
| `GET /api/buscas` | Lista as buscas já feitas |
| `GET /api/buscas/{id}` | Status e progresso de uma busca |
| `GET /api/leads` | Lista com filtros: busca, nota, status, texto, excluídos |
| `GET /api/leads/{id}` | Um lead com motivos da nota e mensagem já preenchida |
| `PATCH /api/leads/{id}` | Muda status, anotação ou a mensagem editada |
| `POST /api/leads/reavaliar` | Recalcula as notas depois que o perfil mudou |
| `GET /api/exportar` | Baixa um CSV dos leads filtrados |

Fluxo de uma busca: o painel envia `POST /api/buscas`, o servidor geocodifica a cidade (Nominatim), cria o job no motor, acompanha o status em segundo plano, baixa o CSV quando termina, limpa e pontua cada linha e grava no SQLite. O painel só consulta o progresso.

Armazenamento em `dados/leads.db` (SQLite):

- **buscas:** id, data, parâmetros, status, id do job no motor.
- **leads:** dados do Maps, nota, letra, motivos, status (novo, contatado, respondeu, fechado, descartado), anotação, mensagem editada.
- **Duplicados:** o mesmo negócio em buscas diferentes vira um lead só. A chave é o identificador do Maps se o CSV trouxer um, senão o nome mais o endereço normalizados. Colunas conferidas na fase 0 com um CSV real (36 colunas, lista em `fase0-verificacao-motor.md`). `place_id` e `cid` vieram preenchidos em todas as linhas e servem de chave contra duplicados. `order_online` e `reservations` chegam como JSON, não como texto simples. `emails` só vem preenchido quando o job usa a opção de e-mail (`email: true`), e isso deixa a busca mais lenta. Na API do motor o campo `lang` usa código de duas letras (`pt`), e `pt-BR` é recusado.
- A exportação da v1 é CSV em UTF-8 com BOM, pra abrir certo no Excel. Planilha `.xlsx` fica pra depois, porque exigiria uma biblioteca.

Segurança do servidor local, porque uma página qualquer da internet pode tentar falar com `127.0.0.1`:

- Aceita só requisições com `Host` igual a `127.0.0.1:8787` ou `localhost:8787`.
- Gera um token a cada início, entrega só ao painel e exige o token em toda rota que altera algo.
- Não libera CORS pra nenhuma origem.
- Não lê nem grava nada fora da pasta do kit.

## Painel

O painel é uma página estática (`index.html`, `app.js`, `estilo.css`) sem framework e sem build. Ela só conversa com a API da seção anterior. A referência visual é o preview já aprovado na direção (prata e grafite, minimalista, tema claro e escuro); o refinamento do design fica pra depois, sem mexer na API.

| Tela | O que faz | Dados |
| --- | --- | --- |
| Buscar | Escolhe tipos de negócio (sugeridos pelo perfil), UF e cidade, cobertura da cidade e tamanho da busca (rápida, média, ampla), extras de e-mail e redes. Mostra progresso | `POST /api/buscas`, `GET /api/buscas/{id}` |
| Leads | Tabela com nota A, B, C, filtros, busca por texto, status e exportação. Ao abrir um lead: motivos da nota, mensagem editada na hora, botões de copiar e abrir WhatsApp | `GET /api/leads`, `PATCH /api/leads/{id}`, `GET /api/exportar` |
| Minha oferta | Edita o perfil: oferta, tom, regras e pesos, exclusões e os modelos de mensagem. Salvar recalcula as notas | `GET` e `PUT /api/perfil`, `POST /api/leads/reavaliar` |

Comportamentos que valem desde a v1:

- Se o perfil não existe ou não é válido, o painel abre numa tela que explica como rodar a entrevista na IA, em vez de quebrar.
- Se o motor está desligado, mostra um aviso com o comando pra subir, e a aba Leads continua funcionando com o que já foi salvo.
- O aviso de conformidade da pergunta 12 fica fixo no topo da aba Leads quando aplicável.
- Abrir o WhatsApp usa o link `wa.me` com a mensagem preenchida. O envio é sempre manual, uma pessoa por vez. Sem disparo automático.
- O painel avisa uma vez, na primeira busca grande, sobre o risco de bloqueio temporário do IP.
- Respeita `prefers-reduced-motion` e funciona em tela de notebook e de celular.

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

Depois da fase 5, fora do escopo da v1: refino do design do painel, motor como programa direto (sem Docker, ver `fase0-verificacao-motor.md`), exportação `.xlsx` e uma segunda versão do kit.

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
