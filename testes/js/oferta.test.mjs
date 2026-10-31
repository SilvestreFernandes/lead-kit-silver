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
