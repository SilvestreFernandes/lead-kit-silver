// Tela Minha oferta: funções puras (rascunho, conferência, limpeza, notas e prévia das mensagens).
import test from 'node:test';
import assert from 'node:assert/strict';

const u = await import('../../kit/painel/oferta-util.js');

const OPCOES = {
  peso_minimo: 0, peso_maximo: 5,
  marcadores: ['nome', 'cidade', 'categoria', 'motivo', 'meu_nome', 'minha_empresa'],
  regras: [{ id: 'sem_site' }, { id: 'so_instagram' }, { id: 'nota_alta' }, { id: 'celular' }],
  cortes_padrao: { a: 0.7, b: 0.4 },
};

const perfilBase = () => ({
  versao: 1, criado_em: '2026-10-29',
  negocio: { nome: 'Ana', empresa: 'Estúdio', oferta: 'Sites para negócios locais', atendimento: 'remoto' },
  cliente: { tipos: ['padaria'], regioes: ['Brasília-DF'], porte: 'pequeno', exemplo: '' },
  pontuacao: { regras: [{ id: 'celular', peso: 2 }, { id: 'sem_site', peso: 3 }] },
  exclusoes: ['franquia'], exclusoes_concorrentes: [],
  abordagem: { canais: ['whatsapp'], tom: 'amigavel', oferta_entrada: 'diagnóstico grátis', volume_semana: '10-30' },
  conformidade: { restricoes: 'nao' },
  mensagens: { whatsapp: 'Oi, {nome}! Se não fizer sentido, é só avisar que não escrevo mais.' },
});

test('rascunho: completa o que falta e guarda o que a tela não conhece', () => {
  const r = u.rascunhoDoPerfil({ negocio: { oferta: 'x' }, campo_novo: { a: 1 } });
  assert.equal(r.negocio.nome, '');
  assert.deepEqual(r.cliente.tipos, []);
  assert.deepEqual(r.exclusoes_categorias, []);
  assert.deepEqual(r.campo_novo, { a: 1 });
  for (const ruim of [null, undefined, 'texto', 5, []]) assert.ok(u.rascunhoDoPerfil(ruim).negocio);
});

test('rascunho não é o mesmo objeto do perfil: mexer nele não muda o original', () => {
  const p = perfilBase();
  const r = u.rascunhoDoPerfil(p);
  r.cliente.tipos.push('academia');
  assert.deepEqual(p.cliente.tipos, ['padaria']);
});

test('listas: tira espaços, não repete (sem diferenciar maiúscula) e ignora vazio', () => {
  let l = [];
  l = u.adicionarNaLista(l, '  Padaria  ');
  assert.deepEqual(l, ['Padaria']);
  assert.equal(u.adicionarNaLista(l, 'padaria'), l);
  assert.equal(u.adicionarNaLista(l, '   '), l);
  assert.equal(u.adicionarNaLista(l, null), l);
  assert.deepEqual(u.adicionarNaLista(l, 'Casa   de   café'), ['Padaria', 'Casa de café']);
  assert.deepEqual(u.removerDaLista(['a', 'b', 'c'], 1), ['a', 'c']);
  assert.equal(u.adicionarNaLista([], 'x'.repeat(500))[0].length, u.LIMITE_DO_TEXTO);
});

test('resposta 12: ida e volta sem perder o detalhe', () => {
  assert.deepEqual(u.restricaoParaForm('nao'), { resposta: 'nao', detalhe: '' });
  assert.deepEqual(u.restricaoParaForm(''), { resposta: 'nao', detalhe: '' });
  assert.deepEqual(u.restricaoParaForm('Não sei'), { resposta: 'nao sei', detalhe: '' });
  assert.deepEqual(u.restricaoParaForm('sim: conselho de classe'), { resposta: 'sim', detalhe: 'conselho de classe' });
  assert.deepEqual(u.restricaoParaForm('Conselho de odontologia'), { resposta: 'sim', detalhe: 'Conselho de odontologia' });
  assert.equal(u.restricaoParaPerfil({ resposta: 'sim', detalhe: ' CRO ' }), 'sim: CRO');
  assert.equal(u.restricaoParaPerfil({ resposta: 'sim', detalhe: '' }), 'sim');
  assert.equal(u.restricaoParaPerfil({ resposta: 'nao sei', detalhe: 'x' }), 'nao sei');
  assert.equal(u.restricaoParaPerfil({ resposta: 'nao', detalhe: 'x' }), 'nao');
});

test('cortes automáticos: 70% e 40% da soma, para cima (mesma conta do kit)', () => {
  assert.deepEqual(u.cortesAutomaticos(10), { a: 7, b: 4 });
  assert.deepEqual(u.cortesAutomaticos(7), { a: 5, b: 3 });
  assert.deepEqual(u.cortesAutomaticos(1), { a: 1, b: 1 });
  assert.deepEqual(u.cortesAutomaticos(0), { a: 0, b: 0 });
  assert.equal(u.somaDosPesos([{ peso: 3 }, { peso: 2 }, { peso: NaN }]), 5);
});

test('prévia: troca os marcadores e avisa dos desconhecidos, sem quebrar', () => {
  const ex = u.exemploDePrevia(perfilBase(), { sem_site: 'não achei um site' });
  const { texto, desconhecidos } = u.previaDaMensagem('Oi, {nome}! Sou {meu_nome}, da {minha_empresa}. {motivo}. {coisa}', ex, OPCOES.marcadores);
  assert.equal(texto, 'Oi, Padaria Exemplo! Sou Ana, da Estúdio. não achei um site. {coisa}');
  assert.deepEqual(desconhecidos, ['coisa']);
  const vazio = u.previaDaMensagem('Oi, {meu_nome}', { meu_nome: '' }, OPCOES.marcadores);
  assert.equal(vazio.texto, 'Oi, {meu_nome}');
});

test('inserir marcador: no cursor, no lugar da seleção ou no fim', () => {
  assert.deepEqual(u.inserirMarcador('Oi, !', 4, 4, 'nome'), { texto: 'Oi, {nome}!', cursor: 10 });
  assert.deepEqual(u.inserirMarcador('Oi, XX!', 4, 6, 'nome'), { texto: 'Oi, {nome}!', cursor: 10 });
  assert.deepEqual(u.inserirMarcador('Oi', undefined, undefined, 'nome'), { texto: 'Oi{nome}', cursor: 8 });
  assert.deepEqual(u.inserirMarcador('', 50, 99, 'cidade'), { texto: '{cidade}', cursor: 8 });
});

test('conferir: o perfil de exemplo passa; cada campo obrigatório vazio é apontado', () => {
  assert.deepEqual(u.conferirRascunho(u.rascunhoDoPerfil(perfilBase()), OPCOES), []);
  const r = u.rascunhoDoPerfil({});
  const campos = u.conferirRascunho(r, OPCOES).map((e) => e.campo);
  assert.deepEqual(campos, ['oferta', 'tipos', 'regioes', 'canais', 'tom']);
});

test('conferir: peso fora de 0 a 5, cortes errados e listas que faltam', () => {
  const r = u.rascunhoDoPerfil(perfilBase());
  r.pontuacao.regras[0].peso = 9;
  r.pontuacao.corte_a = 3; r.pontuacao.corte_b = 5;
  r.exclusoes = ['concorrente', 'categoria'];
  r.mensagens.whatsapp = 'Oi {nome} {cep}';
  const campos = u.conferirRascunho(r, OPCOES).map((e) => e.campo);
  assert.deepEqual(campos, ['pesos', 'cortes', 'concorrentes', 'categorias', 'mensagem-whatsapp']);
  r.pontuacao.corte_a = 5; r.pontuacao.corte_b = 3; r.pontuacao.regras[0].peso = 5;
  r.exclusoes_concorrentes = ['Fulano']; r.exclusoes_categorias = ['igreja']; r.mensagens.whatsapp = 'Oi {nome}';
  assert.deepEqual(u.conferirRascunho(r, OPCOES), []);
});

test('para salvar: aparado, regras na ordem do kit, listas de exclusão só se a exclusão está ligada', () => {
  const r = u.rascunhoDoPerfil(perfilBase());
  r.negocio.oferta = '  Sites   e  automação  ';
  r.exclusoes_concorrentes = ['Fulano'];
  r.mensagens.email = '   ';
  const p = u.perfilParaSalvar(r, OPCOES);
  assert.equal(p.negocio.oferta, 'Sites e automação');
  assert.deepEqual(p.pontuacao.regras.map((x) => x.id), ['sem_site', 'celular']);
  assert.deepEqual(p.exclusoes_concorrentes, []);
  assert.equal('email' in p.mensagens, false);
  assert.equal('corte_a' in p.pontuacao, false);
  assert.equal(r.negocio.oferta, '  Sites   e  automação  ');  // o rascunho não muda
});

test('para salvar: mantém cortes manuais e remove regra que o kit não conhece', () => {
  const r = u.rascunhoDoPerfil(perfilBase());
  r.pontuacao.regras.push({ id: 'regra_velha', peso: 1 });
  r.pontuacao.corte_a = 6; r.pontuacao.corte_b = 3;
  const p = u.perfilParaSalvar(r, OPCOES);
  assert.deepEqual([p.pontuacao.corte_a, p.pontuacao.corte_b], [6, 3]);
  assert.ok(!p.pontuacao.regras.some((x) => x.id === 'regra_velha'));
});

test('mudou: compara por conteúdo', () => {
  assert.equal(u.mudou({ a: [1] }, { a: [1] }), false);
  assert.equal(u.mudou({ a: [1] }, { a: [2] }), true);
});

test('resumo ao salvar: singular, plural e sem leads', () => {
  assert.match(u.resumoDaReavaliacao({ leads: 1, por_letra: { A: 1, B: 0, C: 0 } }), /1 lead recebeu nota de novo: 1 A, 0 B e 0 C/);
  assert.match(u.resumoDaReavaliacao({ leads: 262, por_letra: { A: 10, B: 50, C: 202 } }), /262 leads receberam nota de novo: 10 A, 50 B e 202 C/);
  assert.match(u.resumoDaReavaliacao({ leads: 0, por_letra: {} }), /Ainda não há leads/);
});

// ---------- etapa 2: importância, etapas e ordem das regras

test('importância: Ignorar 0, Pouco 1, Importa 2, Muito 3; 4 e 5 viram Personalizado sem perder o valor', () => {
  assert.deepEqual(u.NIVEIS_DE_PESO.map((n) => [n.id, n.peso]), [['ignorar', 0], ['pouco', 1], ['importa', 2], ['muito', 3]]);
  for (const [peso, nivel] of [[0, 'ignorar'], [1, 'pouco'], [2, 'importa'], [3, 'muito'], [4, 'personalizado'], [5, 'personalizado']]) {
    assert.equal(u.nivelDoPeso(peso), nivel, String(peso));
  }
  const regras = [{ id: 'sem_site', peso: 5 }, { id: 'celular', peso: 2 }];
  assert.equal(u.pesoDaRegra(regras, 'sem_site'), 5);
  assert.equal(u.pesoDaRegra(regras, 'delivery'), 0);  // ausente conta como Ignorar
  const mexido = u.definirNivel(regras, 'celular', 'muito', regras);
  assert.deepEqual(mexido, [{ id: 'sem_site', peso: 5 }, { id: 'celular', peso: 3 }]);  // o 5 continua 5
  assert.deepEqual(regras, [{ id: 'sem_site', peso: 5 }, { id: 'celular', peso: 2 }]);  // a lista de entrada não muda
});

test('importância: os pesos padrão do kit (1, 2 e 3) viram nível e voltam com o mesmo valor', () => {
  for (const padrao of [1, 2, 3]) {
    const nivel = u.nivelDoPeso(padrao);
    assert.notEqual(nivel, 'personalizado');
    const depois = u.definirNivel([], 'sem_site', nivel, []);
    assert.equal(u.pesoDaRegra(depois, 'sem_site'), padrao);
  }
});

test('importância: Ignorar tira a regra, mas respeita um peso 0 que já estava no perfil', () => {
  const original = [{ id: 'a', peso: 0 }, { id: 'b', peso: 2 }];
  assert.deepEqual(u.definirNivel(original, 'b', 'ignorar', original), [{ id: 'a', peso: 0 }]);
  assert.deepEqual(u.definirNivel([{ id: 'b', peso: 2 }], 'a', 'muito', original), [{ id: 'b', peso: 2 }, { id: 'a', peso: 3 }]);
  assert.deepEqual(u.definirNivel([{ id: 'b', peso: 2 }, { id: 'a', peso: 3 }], 'a', 'ignorar', original), [{ id: 'b', peso: 2 }, { id: 'a', peso: 0 }]);
  assert.deepEqual(u.definirNivel([], 'x', 'ignorar', original), []);  // ligar e desligar não deixa rastro
  assert.equal(u.definirNivel(original, 'a', 'nao-existe', original), original);
});

test('ordem das regras: as que já estavam no perfil não mudam de lugar ao salvar', () => {
  const p = perfilBase();
  p.pontuacao.regras = [{ id: 'celular', peso: 4 }, { id: 'sem_site', peso: 5 }];
  const original = u.rascunhoDoPerfil(p);
  const r = u.copiar(original);
  r.negocio.oferta = 'Outra frase';
  const salvo = u.perfilParaSalvar(r, OPCOES, original);
  assert.deepEqual(salvo.pontuacao.regras, [{ id: 'celular', peso: 4 }, { id: 'sem_site', peso: 5 }]);  // ordem e pesos 4 e 5 intactos
  r.pontuacao.regras = u.definirNivel(r.pontuacao.regras, 'nota_alta', 'importa', original.pontuacao.regras);
  r.pontuacao.regras = u.definirNivel(r.pontuacao.regras, 'so_instagram', 'pouco', original.pontuacao.regras);
  const novo = u.perfilParaSalvar(r, OPCOES, original);
  assert.deepEqual(novo.pontuacao.regras.map((x) => x.id), ['celular', 'sem_site', 'so_instagram', 'nota_alta']);  // novas depois, na ordem do kit
});

test('sem mexer em nada, o rascunho é igual ao original (a barra de salvar não aparece)', () => {
  const original = u.rascunhoDoPerfil(perfilBase());
  assert.equal(u.mudou(u.copiar(original), original), false);
  const r = u.copiar(original);
  r.pontuacao.regras = u.definirNivel(r.pontuacao.regras, 'sem_site', 'muito', original.pontuacao.regras);  // já era 3
  assert.equal(u.mudou(r, original), false);
});

test('etapas: cada campo tem a sua, e o erro do servidor leva à etapa certa', () => {
  assert.deepEqual(u.ETAPAS.map((e) => e.nome), ['Sobre você', 'Quem atender', 'O que importa', 'O que evitar', 'Como falar']);
  for (const [campo, etapa] of [['oferta', 1], ['regioes', 2], ['porte', 2], ['pesos', 3], ['cortes', 3], ['concorrentes', 4], ['canais', 5], ['mensagem-whatsapp', 5], ['volume', 5]]) {
    assert.equal(u.etapaDoCampo(campo), etapa, campo);
  }
  const casos = [
    ['Falta preencher: o que você vende (negocio.oferta).', 1],
    ['Falta preencher: os tipos de negócio que você quer atender (cliente.tipos).', 2],
    ['Falta preencher: onde você atende (cliente.regioes).', 2],
    ['O porte do cliente precisa ser: pequeno, medio.', 2],
    ['Falta preencher: como você prefere abordar (abordagem.canais).', 5],
    ['O tom precisa ser: amigavel, direto, formal.', 5],
    ['A mensagem de WhatsApp usa o marcador inválido {apelido}.', 5],
    ['A mensagem de e-mail precisa de uma saída clara.', 5],
    ['Os cortes A e B estavam errados.', 3],
    ['Versão do perfil desconhecida (2). Refaça a entrevista.', 1],
    [undefined, 1],
  ];
  for (const [msg, etapa] of casos) assert.equal(u.etapaDoErro(msg), etapa, String(msg));
});

// ---------- qual nível fica marcado (função pura que a tela só obedece)

import { readFileSync } from 'node:fs';
const REGRAS_DO_KIT = JSON.parse(readFileSync(new URL('../../kit/regras.json', import.meta.url), 'utf-8'));

const controlesFalsos = () => ({
  ignorar: {}, pouco: {}, importa: {}, muito: {},
  personalizado: { hidden: true }, rotuloPersonalizado: { hidden: true }, textoPersonalizado: { textContent: '' },
});
const marcados = (c) => ['ignorar', 'pouco', 'importa', 'muito', 'personalizado'].filter((n) => c[n].checked);

test('nível marcado: cada peso de 0 a 5 devolve o nível certo', () => {
  const esperado = { 0: 'ignorar', 1: 'pouco', 2: 'importa', 3: 'muito', 4: 'personalizado', 5: 'personalizado' };
  for (const [peso, nivel] of Object.entries(esperado)) {
    const e = u.estadoDosNiveis([{ id: 'sem_site', peso: Number(peso) }], 'sem_site');
    assert.equal(e.marcado, nivel, `peso ${peso}`);
    assert.equal(e.personalizado, nivel === 'personalizado');
    assert.equal(e.rotuloPersonalizado, nivel === 'personalizado' ? String(peso) : '');
    assert.equal(e.peso, Number(peso));
  }
});

test('nível marcado: todos os pesos padrão do kit caem em Pouco, Importa ou Muito', () => {
  const regras = Object.entries(REGRAS_DO_KIT.regras);
  assert.equal(regras.length, 10);
  for (const [id, cfg] of regras) {
    const e = u.estadoDosNiveis([{ id, peso: cfg.peso }], id);
    assert.ok(['pouco', 'importa', 'muito'].includes(e.marcado), `${id} peso ${cfg.peso} caiu em ${e.marcado}`);
    assert.equal(e.personalizado, false, id);
    assert.equal(u.NIVEIS_DE_PESO.find((n) => n.id === e.marcado).peso, cfg.peso, id);  // volta ao mesmo peso
  }
});

test('nível marcado: regra ausente do perfil devolve Ignorar (e lista vazia também)', () => {
  assert.equal(u.estadoDosNiveis([{ id: 'celular', peso: 2 }], 'delivery').marcado, 'ignorar');
  assert.equal(u.estadoDosNiveis([], 'delivery').marcado, 'ignorar');
  assert.equal(u.estadoDosNiveis([], 'delivery').personalizado, false);
});

test('botões: sempre exatamente um marcado e o Personalizado só aparece com peso 4 ou 5', () => {
  for (let peso = 0; peso <= 5; peso += 1) {
    const c = controlesFalsos();
    // começa de um estado sujo, como o de um botão que a pessoa clicou antes
    for (const n of ['ignorar', 'pouco', 'importa', 'muito', 'personalizado']) c[n].checked = true;
    u.marcarNiveis(c, u.estadoDosNiveis([{ id: 'x', peso }], 'x'));
    assert.equal(marcados(c).length, 1, `peso ${peso}`);
    assert.equal(marcados(c)[0], u.nivelDoPeso(peso));
    const custom = peso >= 4;
    assert.equal(c.personalizado.hidden, !custom);
    assert.equal(c.rotuloPersonalizado.hidden, !custom);
    assert.equal(c.textoPersonalizado.textContent, custom ? String(peso) : '');
  }
  const c = controlesFalsos();
  u.marcarNiveis(c, u.estadoDosNiveis([], 'x'));
  assert.deepEqual(marcados(c), ['ignorar']);  // regra ausente
});

test('abrir a tela e salvar sem mexer não muda nenhum peso, nem a ordem', () => {
  const perfis = [
    [{ id: 'sem_site', peso: 3 }, { id: 'so_instagram', peso: 2 }, { id: 'nota_alta', peso: 2 }, { id: 'muitas_avaliacoes', peso: 1 }, { id: 'celular', peso: 2 }],
    [{ id: 'celular', peso: 4 }, { id: 'sem_site', peso: 5 }, { id: 'nota_alta', peso: 0 }, { id: 'reserva', peso: 1 }],
    [],
    Object.entries(REGRAS_DO_KIT.regras).map(([id, cfg]) => ({ id, peso: cfg.peso })).reverse(),
  ];
  const opcoes = { ...OPCOES, regras: Object.keys(REGRAS_DO_KIT.regras).map((id) => ({ id })) };
  for (const regras of perfis) {
    const p = perfilBase();
    p.pontuacao.regras = regras.map((r) => ({ ...r }));
    const original = u.rascunhoDoPerfil(p);
    const aberto = u.copiar(original);
    // a tela mostra cada regra com estadoDosNiveis; olhar não altera nada
    for (const { id } of opcoes.regras) u.estadoDosNiveis(aberto.pontuacao.regras, id);
    assert.equal(u.mudou(aberto, original), false);  // a barra de salvar nem aparece
    const salvo = u.perfilParaSalvar(aberto, opcoes, original);
    assert.deepEqual(salvo.pontuacao.regras, regras);  // mesmos pesos, mesma ordem
  }
});
