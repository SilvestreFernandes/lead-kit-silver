# Roteiro da entrevista

Este arquivo é o roteiro que a IA segue para fazer a entrevista. São 12 perguntas, sempre nesta ordem. O texto de cada pergunta é fixo: a IA não troca, não junta e não pula pergunta. Quem monta o perfil depois é o script `kit/montar_perfil.py`, a partir do arquivo `dados/respostas.json`.

## Regras para a IA

1. Faça **uma pergunta por vez**. Mostre as opções numeradas e, nas perguntas com opções, termine sempre com "Outra resposta".
2. Use palavras simples. Na primeira vez que aparecerem, explique "lead" (um negócio que pode virar seu cliente) e "nota" (A, B ou C, de quem vale falar primeiro).
3. Se a resposta vier vaga, repita ou esclareça a pergunta **no máximo uma vez**. Depois disso, aceite o que veio ou deixe vazio. Nunca responda pela pessoa e nunca invente resposta.
4. **Grave cada resposta em `dados/respostas.json` logo depois de recebê-la**, no formato indicado em cada pergunta. Assim a entrevista pode parar e voltar sem perder nada. Para saber o que falta, rode `python kit/montar_perfil.py estado`.
5. Não peça CPF, senha, número de cartão, dado de saúde nem dado de clientes da pessoa. Se ela escrever algo assim, não grave e explique que o perfil não guarda isso.
6. No fim, rode `python kit/montar_perfil.py resumo`, mostre o resumo e **só grave o perfil depois da pessoa dizer "confirmo"** (`python kit/montar_perfil.py montar`).
7. Para refazer, a pessoa pede "refazer perfil". O perfil antigo vira `perfil.anterior.json` (`python kit/montar_perfil.py montar --refazer`).

O arquivo `dados/respostas.json` tem as respostas por número da pergunta, assim:

```json
{
  "versao": 1,
  "1": "texto",
  "2": {"nome": "texto", "empresa": "texto"},
  "...": "..."
}
```

---

## Pergunta 1

- **Texto:** O que você vende, em uma frase?
- **Obrigatória:** sim
- **Campo do perfil:** `negocio.oferta`
- **Resposta no arquivo:** `"1": "texto"`
- **Opções:** texto livre, até 300 caracteres.
- **Como tratar:** se vier vaga ("vendo coisas"), pergunte uma vez o que a pessoa faz por quem compra.

## Pergunta 2

- **Texto:** Qual é o seu nome e o da sua empresa (se tiver)?
- **Obrigatória:** sim
- **Campo do perfil:** `negocio.nome`, `negocio.empresa`
- **Resposta no arquivo:** `"2": {"nome": "texto", "empresa": "texto"}`
- **Opções:** texto livre. O nome é obrigatório; a empresa pode ficar vazia (`""`) se a pessoa não tiver.
- **Como tratar:** o nome vai nas mensagens de abordagem. Peça o nome como a pessoa quer ser chamada.

## Pergunta 3

- **Texto:** Quem é o seu cliente ideal?
- **Obrigatória:** sim
- **Campo do perfil:** `cliente.tipos`, `cliente.porte`
- **Resposta no arquivo:** `"3": {"tipos": ["texto"], "porte": "id"}`
- **Opções:**
  - Tipos de negócio: texto livre, um ou mais (por exemplo padaria, academia, clínica de estética).
  - Porte do negócio (uma só):
    1. Pequeno (`pequeno`)
    2. Médio (`medio`)
    3. Grande (`grande`)
    4. Qualquer (`qualquer`)
    5. Outra resposta (texto livre, sem efeito no perfil)
- **Como tratar:** pergunte primeiro os tipos de negócio e depois o porte.

## Pergunta 4

- **Texto:** Onde você atende?
- **Obrigatória:** sim
- **Campo do perfil:** `cliente.regioes`, `negocio.atendimento`
- **Resposta no arquivo:** `"4": {"regioes": ["Cidade-UF"], "atendimento": "id"}`
- **Opções:**
  - Regiões: cidades e estados no formato Cidade-UF (por exemplo Brasília-DF), ou "Todo o Brasil".
  - Como atende (uma só):
    1. Presencial (`presencial`)
    2. Remoto (`remoto`)
    3. Os dois (`ambos`)
    4. Outra resposta (texto livre, sem efeito no perfil)
- **Como tratar:** se a pessoa escrever só a cidade, pergunte o estado.

## Pergunta 5

- **Texto:** O que faz um negócio ser um bom lead pra você?
- **Obrigatória:** sim
- **Campo do perfil:** `pontuacao.regras`
- **Resposta no arquivo:** `"5": {"regras": ["id"], "outro": ""}`
- **Opções:** pode marcar várias.
  1. Não tem site (`sem_site`)
  2. Só usa Instagram ou Facebook (`so_instagram`)
  3. Nota baixa no Google (`nota_baixa`)
  4. Nota alta no Google (`nota_alta`)
  5. Poucas avaliações (`poucas_avaliacoes`)
  6. Muitas avaliações (`muitas_avaliacoes`)
  7. Tem delivery (`delivery`)
  8. Aceita reserva (`reserva`)
  9. Sem e-mail publicado (`sem_email`)
  10. Outra resposta (texto livre)
- **Como tratar:** o painel só dá nota por coisas que o Google Maps mostra. "Outra resposta" fica anotada em `"outro"`, mas **não vira regra e não muda a nota**: diga isso com simplicidade. Pelo menos uma opção precisa ser marcada. Os pesos são os padrões do kit; a pessoa pode ajustá-los depois, na tela Minha oferta.

## Pergunta 6

- **Texto:** O que você quer evitar?
- **Obrigatória:** sim
- **Campo do perfil:** `exclusoes`, `exclusoes_concorrentes`, `exclusoes_categorias`
- **Resposta no arquivo:** `"6": {"evitar": ["id"], "concorrentes": ["texto"], "categorias": ["texto"], "outro": ""}`
- **Opções:** pode marcar várias, ou nenhuma.
  1. Redes e franquias (`franquia`)
  2. Categorias específicas (`categoria`)
  3. Concorrentes (`concorrente`)
  4. Sem telefone (`sem_telefone`)
  5. Nota muito baixa (`nota_muito_baixa`)
  6. Outra resposta (texto livre)
- **Desdobramento (continua sendo a pergunta 6, não é uma 13ª pergunta):**
  - Se marcar "Concorrentes" (3), pergunte quais: nomes ou sites, separados por vírgula. Grave em `"concorrentes"`.
  - Se marcar "Categorias específicas" (2), pergunte quais categorias evitar (por exemplo igreja, escola). Grave em `"categorias"`.
  - Não deixe a lista vazia com a opção marcada: o script recusa.
- **Como tratar:** "Outra resposta" fica anotada em `"outro"`, mas não vira regra.

## Pergunta 7

- **Texto:** Quem foi o seu melhor cliente até hoje?
- **Obrigatória:** não (opcional)
- **Campo do perfil:** `cliente.exemplo`
- **Resposta no arquivo:** `"7": "texto"`
- **Opções:** texto livre, até 300 caracteres. Pode ficar vazio (`""`).
- **Como tratar:** só serve para lembrar quem funciona bem. Não muda a nota. Não aceite nome de pessoa nem dados do cliente: peça só o tipo de negócio.

## Pergunta 8

- **Texto:** Como você prefere abordar?
- **Obrigatória:** sim
- **Campo do perfil:** `abordagem.canais`
- **Resposta no arquivo:** `"8": ["id"]`
- **Opções:** pode marcar mais de um.
  1. WhatsApp (`whatsapp`)
  2. E-mail (`email`)
  3. Ligação (`ligacao`)
  4. Visita (`visita`)
  5. Outra resposta (texto livre, sem efeito no perfil)
- **Como tratar:** o painel só escreve mensagem para WhatsApp e e-mail. O envio é sempre manual, um negócio por vez.

## Pergunta 9

- **Texto:** Qual o tom das mensagens?
- **Obrigatória:** sim
- **Campo do perfil:** `abordagem.tom`
- **Resposta no arquivo:** `"9": "id"`
- **Opções:** uma só.
  1. Amigável (`amigavel`)
  2. Direto (`direto`)
  3. Formal (`formal`)
  4. Outra resposta (texto livre, sem efeito no perfil)

## Pergunta 10

- **Texto:** Qual é a sua oferta de entrada?
- **Obrigatória:** sim
- **Campo do perfil:** `abordagem.oferta_entrada`
- **Resposta no arquivo:** `"10": "texto"`
- **Opções:** uma só. O texto gravado é o da opção escolhida, ou o que a pessoa escrever em "Outra resposta".
  1. Diagnóstico grátis
  2. Orçamento
  3. Teste gratuito
  4. Reunião rápida
  5. Amostra
  6. Outra resposta (texto livre, até 120 caracteres)

## Pergunta 11

- **Texto:** Quantos contatos você consegue fazer por semana?
- **Obrigatória:** sim
- **Campo do perfil:** `abordagem.volume_semana`
- **Resposta no arquivo:** `"11": "id"`
- **Opções:** uma só.
  1. Até 10 (`ate-10`)
  2. De 10 a 30 (`10-30`)
  3. De 30 a 60 (`30-60`)
  4. Mais de 60 (`mais-60`)
  5. Outra resposta (texto livre, sem efeito no perfil)
- **Como tratar:** esta resposta ajuda a sugerir o tamanho da busca. Volume pequeno, ritmo humano e mensagem pessoal: o kit não faz disparo em massa.

## Pergunta 12

- **Texto:** Sua área tem regras de publicidade ou de abordagem?
- **Obrigatória:** sim
- **Campo do perfil:** `conformidade.restricoes`
- **Resposta no arquivo:** `"12": {"resposta": "id", "detalhe": "texto"}`
- **Opções:** uma só.
  1. Não (`nao`)
  2. Sim (`sim`): pergunte qual é a regra ou o órgão, e grave em `"detalhe"` (por exemplo OAB, conselho de contabilidade).
  3. Não sei (`nao sei`)
- **Como tratar:** com "Sim" ou "Não sei", o painel passa a mostrar um aviso fixo de conformidade. O kit não confere se uma mensagem cumpre essas regras, e isto não é aconselhamento jurídico.
