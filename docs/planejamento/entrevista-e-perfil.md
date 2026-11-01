# Entrevista e perfil do Lead Kit Silver

Documento de planejamento. Vale como especificação para quem for implementar a entrevista, o `perfil.json`, a validação, a nota e os modelos de mensagem. A arquitetura geral do kit está no documento "Arquitetura do Lead Kit Silver".

## Objetivo e fluxo

A entrevista faz o Lead Kit Silver servir a qualquer negócio que venda para empresas, sem uma versão por nicho. Na primeira vez que o usuário cola o prompt, a IA instala o motor, conduz a entrevista e grava um perfil. O painel, as notas dos leads e as mensagens leem esse perfil.

A entrevista roda na IA do usuário (Claude Code ou Codex). O painel nunca chama IA.

1. **Pré-checagem:** a IA detecta o sistema, confere Python e Docker, lista o que vai instalar e pede confirmação.
2. **Instalação:** instala o que faltar e liga o motor local na versão fixada, acessível só pelo próprio computador. Se precisar de reinício ou de outra ação do cliente, pausa e retoma depois (ver `arquitetura.md`).
3. **Entrevista:** 12 perguntas, uma por vez, em português.
4. **Perfil:** a IA grava as respostas em `dados/respostas.json`, uma a uma, e o script `kit/montar_perfil.py` monta o `perfil.json`. Os modelos de mensagem são gerados pelo kit (por tom e canal) e a IA só mostra e ajusta com a pessoa (ver "Modelos de mensagem").
5. **Validação:** um script confere o perfil e aponta o que falta ou está errado.
6. **Teste:** uma busca pequena, com o perfil do usuário, pra confirmar que tudo funciona.
7. **Painel:** abre já configurado. O usuário pode refazer a entrevista ou editar o perfil quando quiser.

## Regras da entrevista

A IA segue um roteiro fixo, pra que o resultado seja parecido em qualquer computador e em qualquer ferramenta.

- Uma pergunta por vez, com opções numeradas e sempre a opção "outra resposta".
- A lista de perguntas é fixa. A IA só repete ou esclarece uma pergunta, no máximo uma vez, quando a resposta vier vaga.
- Linguagem simples, explicando termos como "lead" e "nota" na primeira vez que aparecerem.
- A IA nunca responde pelo usuário. Pergunta pulada deixa o campo vazio, e o validador avisa se ele for obrigatório.
- No fim, mostra um resumo em linguagem natural e só grava o perfil depois do "confirmo".
- Não pede CPF, senhas nem dados de clientes. O perfil fica só no computador do usuário.
- Para refazer, o usuário pede "refazer perfil". O perfil antigo vira `perfil.anterior.json` antes de ser substituído.
- **As respostas são gravadas uma a uma** em `dados/respostas.json` (formato em `entrevista/perguntas.md`). Assim a entrevista pode parar e voltar sem perder nada, e quem monta o perfil é o script `kit/montar_perfil.py`, que não depende de IA e é testado com os três perfis de teste.
- **Desdobramento da pergunta 6 (não é uma 13ª pergunta).** Se a pessoa marcar "concorrentes", a IA pergunta, ainda dentro da pergunta 6, quais são (nomes ou sites, um por vez ou separados por vírgula). Se marcar "categorias específicas", pergunta quais. O script não deixa montar o perfil com "concorrentes" ou "categorias" marcados e a lista vazia.
- **"Outra resposta" nas perguntas 5 e 6** não vira regra, porque as regras vêm só de dados que o Google Maps entrega. A IA diz isso com simplicidade e o texto fica em `dados/respostas.json`, sem efeito na nota.

## As perguntas

São 12 perguntas, e só a 7 é opcional. A última coluna mostra qual campo do perfil cada resposta preenche.

| # | Pergunta | Opções | Campo do perfil |
| --- | --- | --- | --- |
| 1 | O que você vende, em uma frase? | Texto livre | `negocio.oferta` |
| 2 | Qual é o seu nome e o da sua empresa (se tiver)? | Texto livre | `negocio.nome`, `negocio.empresa` |
| 3 | Quem é o seu cliente ideal? | Tipos de negócio em texto livre. Porte: pequeno, médio, grande ou qualquer | `cliente.tipos`, `cliente.porte` |
| 4 | Onde você atende? | Cidades e estados, ou todo o Brasil. Presencial, remoto ou os dois | `cliente.regioes`, `negocio.atendimento` |
| 5 | O que faz um negócio ser um bom lead pra você? | Várias: não tem site, só usa Instagram, nota baixa, nota alta, poucas avaliações, muitas avaliações, tem delivery, aceita reserva, sem e-mail publicado, outro | `pontuacao.regras` |
| 6 | O que você quer evitar? | Redes e franquias, categorias específicas, concorrentes, sem telefone, nota muito baixa, outro (se marcar concorrentes ou categorias, a IA pergunta quais, dentro da mesma pergunta) | `exclusoes`, `exclusoes_concorrentes`, `exclusoes_categorias` |
| 7 | Quem foi o seu melhor cliente até hoje? (opcional) | Texto livre, usado só pra calibrar as regras | `cliente.exemplo` |
| 8 | Como você prefere abordar? | WhatsApp, e-mail, ligação, visita, mais de um | `abordagem.canais` |
| 9 | Qual o tom das mensagens? | Amigável, direto ou formal | `abordagem.tom` |
| 10 | Qual é a sua oferta de entrada? | Diagnóstico grátis, orçamento, teste gratuito, reunião rápida, amostra, outro | `abordagem.oferta_entrada` |
| 11 | Quantos contatos você consegue fazer por semana? | Até 10, de 10 a 30, de 30 a 60, mais de 60 | `abordagem.volume_semana` |
| 12 | Sua área tem regras de publicidade ou de abordagem? | Não, sim (qual), não sei | `conformidade.restricoes` |

A resposta 11 define o tamanho da busca sugerido. A resposta 12 decide se o painel mostra um aviso fixo de conformidade.

## Formato do perfil

O perfil é um arquivo `perfil.json` na pasta `dados/` do kit. É texto simples: a pessoa pode abrir, ler e editar. Exemplo preenchido para quem vende sites a negócios locais:

```json
{
  "versao": 1,
  "criado_em": "2026-10-29",
  "negocio": {
    "nome": "Silvestre",
    "empresa": "BrandForge",
    "oferta": "Sites e automações com IA para negócios locais",
    "atendimento": "remoto"
  },
  "cliente": {
    "tipos": ["clínica de estética", "academia", "restaurante"],
    "porte": "pequeno",
    "regioes": ["Brasília-DF"],
    "exemplo": ""
  },
  "pontuacao": {
    "regras": [
      { "id": "sem_site", "peso": 3 },
      { "id": "so_instagram", "peso": 2 },
      { "id": "nota_alta", "peso": 2 },
      { "id": "muitas_avaliacoes", "peso": 1 },
      { "id": "celular", "peso": 2 }
    ],
    "corte_a": 7,
    "corte_b": 4
  },
  "exclusoes": ["franquia", "sem_telefone"],
  "abordagem": {
    "canais": ["whatsapp"],
    "tom": "amigavel",
    "oferta_entrada": "diagnóstico grátis",
    "volume_semana": "10-30"
  },
  "conformidade": { "restricoes": "nao" },
  "mensagens": {
    "whatsapp": "Oi, {nome}! ...",
    "email": "Assunto: ..."
  }
}
```

Regras do formato:

- Todo campo tem valor padrão seguro. Se a pessoa pular uma pergunta, o campo fica vazio e o painel segue funcionando.
- Os pesos são números inteiros de 0 a 5. Os cortes A e B são calculados pelo kit a partir dos pesos e podem ser ajustados no painel.
- As mensagens são escritas uma vez pela IA, com marcadores entre chaves, e ficam salvas no próprio perfil.
- O campo `versao` permite que atualizações futuras do kit migrem perfis antigos sem pedir a entrevista de novo.

## Como o perfil vira nota

A nota é calculada por código, nunca por IA. Cada regra olha um campo que o Google Maps já entrega e soma o peso definido no perfil. Assim a mesma lista gera sempre a mesma nota, e a pessoa consegue ver o motivo de cada uma.

| Regra | O que verifica | Campo do Maps | Peso padrão |
| --- | --- | --- | --- |
| `sem_site` | Negócio sem site próprio | `website` vazio | 3 |
| `so_instagram` | Site é só uma página de rede social | `website` com instagram.com ou facebook.com | 2 |
| `nota_alta` | Boa reputação | `review_rating` de 4,5 ou mais (4,0 vale 1) | 2 |
| `nota_baixa` | Reputação com espaço pra melhorar | `review_rating` abaixo de 4,0 | 2 |
| `muitas_avaliacoes` | Negócio com movimento | `review_count` de 50 ou mais | 1 |
| `poucas_avaliacoes` | Negócio pouco conhecido | `review_count` abaixo de 15 | 1 |
| `celular` | Telefone que provavelmente é WhatsApp | `phone` com 9 dígitos após o DDD | 2 |
| `delivery` | Aceita pedido online | `order_online` preenchido | 1 |
| `reserva` | Aceita reserva | `reservations` preenchido | 1 |
| `sem_email` | Nenhum e-mail publicado | `emails` vazio | 1 |

Como funciona:

- Na entrevista, só entram no perfil as regras que a pessoa escolheu na pergunta 5. As outras ficam desligadas.
- As exclusões da pergunta 6 não diminuem a nota: o lead sai da lista e aparece num filtro "excluídos", com o motivo.
- A nota final vira A, B ou C pelos cortes do perfil. Cada lead mostra os motivos em linguagem simples, por exemplo "sem site (+3)".
- O telefone com 9 dígitos é uma estimativa. O painel diz "provavelmente WhatsApp", nunca confirma.
- Instagram só é detectado quando o site do negócio aponta pra ele. O kit não promete achar o perfil de todo mundo.
- Os nomes das colunas foram conferidos na fase 0 com um CSV real (ver `fase0-verificacao-motor.md`). `order_online` e `reservations` chegam como JSON, então a regra olha se o valor não é vazio ou `[]`. `emails` só vem preenchido quando a busca usa a opção de e-mail; sem ela, a regra `sem_email` marcaria todo lead, então só vale em buscas feitas com e-mail ligado.

## Modelos de mensagem

Modelo **híbrido** (decidido em 2026-11-01). O kit gera modelos seguros por tom (pergunta 9) e por canal (pergunta 8). A IA pode reescrever a linha da oferta e ajustar o tom junto com a pessoa, mostrando o resultado antes do "confirmo". **Todo texto, venha do kit ou da IA, passa pelo mesmo validador** (`kit/validar_perfil.py`), e só é salvo se passar. O painel só troca os marcadores pelos dados de cada lead. Nenhuma IA é chamada quando a pessoa usa o painel.

Marcadores disponíveis: `{nome}` (nome do negócio), `{cidade}`, `{categoria}`, `{motivo}` (o motivo da nota, em uma frase), `{meu_nome}`, `{minha_empresa}`.

O que o validador exige de cada modelo:

- **Marcadores obrigatórios:** `{meu_nome}`, `{minha_empresa}` e `{motivo}`, e uma linha do que a pessoa oferece (vinda de `negocio.oferta` e da oferta de entrada da pergunta 10).
- **Só marcadores permitidos**, e **nenhum artigo antes de `{nome}`**: "Vi que {nome} tem...", nunca "Vi que a {nome} tem..." nem "o {nome}". O gênero do negócio é desconhecido (ver `arquitetura.md`). O mesmo vale para "da", "do", "na" e "no" antes de `{nome}` e `{categoria}`.
- **Saída clara (opt-out)**, por exemplo "se não fizer sentido, é só me avisar que não escrevo mais".
- **Sem promessa de renda, de resultado ou de quantidade**, e sem pressão ou urgência inventada.
- **Tamanho:** curto, de 3 a 5 linhas, dentro do limite do arquivo.

O que a IA e o kit devem seguir ao escrever:

- Começar pelo negócio do lead, não por quem escreve.
- Terminar com a oferta de entrada e uma pergunta fácil de responder.
- Um modelo por canal escolhido na pergunta 8. Só são salvos depois do "confirmo".

**Gancho.** A abertura da mensagem usa um **gancho**: um fato verificável dos dados do lead (por exemplo "não achei um site no perfil do Google Maps"), vindo de `{motivo}`. O gancho nunca é elogio genérico nem promessa. Cada regra de nota tem a sua frase de abertura em `kit/regras.json`. Regra sem gancho bom (por exemplo só "nota alta") **não gera mensagem automática**: o lead continua com nota e motivo na lista, o painel diz em português simples que não há mensagem pronta para aquele motivo e a pessoa pode escrever a dela. No resumo antes do "confirmo", a IA mostra a abertura de cada regra escolhida e a pessoa pode tirar as que não servem. Isso não é uma pergunta nova.

Exemplo de WhatsApp no tom amigável:

> Oi, tudo bem? Aqui é o {meu_nome}, da {minha_empresa}. Vi que {nome} tem ótimas avaliações em {cidade}, mas {motivo}. Eu faço um diagnóstico grátis com ideias pra isso. Posso te mandar? Se não fizer sentido, é só avisar que não escrevo mais.

## Validação

Antes de o painel abrir, um script simples (`kit/validar_perfil.py`) confere o `perfil.json`. Ele não usa IA: só verifica regras fixas. Se algo estiver errado, mostra uma mensagem em português dizendo o que corrigir, e a IA refaz só aquela pergunta.

| O que confere | Se falhar |
| --- | --- |
| O arquivo existe e é um JSON válido | Pede pra refazer a entrevista |
| `versao` é conhecida | Tenta migrar; se não der, avisa |
| Campos obrigatórios preenchidos: oferta, tipos de cliente, regiões, canais, tom | Pergunta só o que falta |
| Todo `id` de regra existe na tabela de regras | Remove a regra e avisa |
| Pesos são inteiros de 0 a 5 | Ajusta pro limite e avisa |
| `corte_a` é maior que `corte_b` | Recalcula os cortes |
| Cada modelo de mensagem só usa marcadores permitidos | Mostra o marcador inválido |
| Cada modelo tem `{meu_nome}`, `{minha_empresa}`, `{motivo}`, nenhum artigo antes de `{nome}` e sem promessa de renda ou de resultado | Mostra o que falta ou o que sobra |
| Cada modelo tem uma saída clara (opt-out) | Pede pra IA reescrever |
| Sem dados sensíveis no perfil (documentos, senhas, dados de saúde) | Remove o campo e avisa |

O script também serve de teste: roda sobre os perfis de teste da seção abaixo antes de qualquer venda.

## Segurança e conformidade

O kit raspa o Google Maps, o que viola os termos de uso do Google, e lida com telefones e e-mails, que são dados pessoais. O prompt precisa ser honesto sobre isso e ensinar o uso responsável. Isto não é aconselhamento jurídico.

Na instalação:

- A IA lista tudo o que vai instalar e pede confirmação a cada passo. Os comandos de instalação vêm de uma **lista fechada** devolvida pelo kit; a IA os executa só depois do "pode seguir" e nunca inventa outro.
- Antes de um passo que abre a janela de permissão de administrador do Windows, a IA avisa e diz que a pessoa precisa clicar nela.
- O Docker Desktop tem termos de uso próprios (a licença depende do tamanho da empresa). O prompt e o guia mandam a pessoa **conferir os termos** antes de instalar, sem afirmar mais nada sobre eles.
- O guia avisa que o Claude Code vai pedir permissão para cada comando e que isso é normal: é a própria ferramenta pedindo, e a pessoa aprova um por vez.
- O prompt nunca manda a pessoa desligar permissões de segurança da ferramenta dela.
- O motor roda só em `127.0.0.1`, sem exposição na internet.
- A versão do motor fica fixada (`gosom/google-maps-scraper:v1.18.1`) e os créditos e a licença MIT do autor original ficam no kit.

Na entrevista:

- A IA não pede documentos, senhas, dados bancários nem dados de saúde.
- A pergunta 12 identifica áreas com regras de publicidade, como advocacia e medicina, e o painel passa a mostrar um aviso fixo.

No uso:

- Os leads ficam só no computador da pessoa. O kit não envia nada pra servidor nenhum.
- Aviso sobre a LGPD: usar contato de empresa pra oferta relacionada ao negócio dela, sem insistir, e parar quando a pessoa pedir.
- Aviso sobre WhatsApp: envio em massa pode banir o número. O kit sugere volume pequeno, ritmo humano e mensagem personalizada, sem bot de disparo.
- O kit recusa uso pra perseguir pessoas, golpes, spam ou assédio, e não monta lista de pessoas físicas, só de negócios.
- Buscas grandes avisam uma vez do risco de bloqueio temporário do IP, sem travar o uso.

## Perfis de teste

Antes de vender, o kit roda a entrevista inteira com três perfis bem diferentes, no Windows do Silvestre. A ideia é provar que funciona pra qualquer nicho, não só pra quem vende site.

| Perfil | O que vende | Quem é o lead | O que deve acontecer |
| --- | --- | --- | --- |
| Agência de sites | Sites e automações | Clínicas, academias, restaurantes sem site ou só com Instagram | Leads sem site ficam no topo (A) |
| Fornecedor B2B | Embalagens para restaurantes | Restaurantes e padarias com movimento | Nota alta e muitas avaliações pesam mais, site não importa |
| Profissional regulado | Contabilidade para pequenos negócios | Comércios locais | Painel mostra o aviso de conformidade e a mensagem não promete resultado |

Critérios de aprovação:

- A entrevista termina em menos de 10 minutos, sem a IA pular ou inventar resposta.
- O `perfil.json` passa na validação de primeira.
- A mesma busca gera listas com ordem diferente conforme o perfil.
- As mensagens usam fatos reais do lead e têm saída clara.
- "Refazer perfil" guarda o anterior em `perfil.anterior.json`.
- O mesmo prompt funciona em pelo menos duas ferramentas (Claude Code e Codex), e só prometemos no material de venda o que foi testado.

## Critérios de pronto da fase 4 (mensagens)

Anotados em 2026-10-30 e decididos em 2026-11-01. Os testes da fase 4 conferem cada um com perfis fictícios.

- **O modelo final de mensagem sempre contém** `{meu_nome}`, `{minha_empresa}`, `{motivo}` e uma linha do que a pessoa oferece. Mensagem sem essas partes não é salva.
- **Cada regra de nota tem uma frase de abertura** que afirma só um fato verificável dos dados do lead, nunca elogio genérico nem promessa.
- **Regra sem gancho bom não gera mensagem automática.** O lead continua com nota e motivo na lista, e o painel diz em português simples que não há mensagem pronta, sem inventar uma abertura.
- **Um só validador** para o texto do kit e para o texto reescrito pela IA.

## Material de venda

Até passar o ensaio de cada caso, o material de venda só cita o que foi testado: **Windows x64 e Claude Code**. macOS, Linux e Codex só entram depois de um ensaio aprovado de cada um. Nenhum texto afirma acessibilidade (o leitor de tela não foi testado).

## Pontos em aberto

Decisões que ainda dependem do Silvestre ou de teste. A IA que implementa deve parar e perguntar antes de decidir qualquer uma delas.

- Perguntas: alguma está sobrando ou faltando pro público? A 12 e a 7 são as mais fáceis de cortar.
- Pesos padrão das regras: ajustar depois de testar com leads reais.
- Motor como programa direto, sem Docker: pesquisa futura, fora da v1. A decisão de usar Docker foi tomada em 2026-10-29.
- Se o prompt funciona igual no Codex e no Claude Code, ou se precisa de uma versão por ferramenta.
- Parcelamento do Kiwify: conferir se os 12x de R$ 97 saem sem juros pro cliente (menos de R$ 10 por mês).
- Disponibilidade do nome Lead Kit Silver (registro.br, Instagram e TikTok).
- Conversa com o mentor sobre o que é próprio e o que vem do repositório aberto, mantendo licença e créditos.
- Visual do painel: refinar depois, com o fluxo já testado.
