// Testes das funções puras e do cliente da API do painel. Rodam com `node --test`.
// O Node é só uma ferramenta de desenvolvimento: o kit em si não depende dele.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as util from '../../kit/painel/util.js';
import * as api from '../../kit/painel/api.js';

test('montarQuery ignora vazio, nulo e falso e codifica o resto', () => {
  assert.equal(util.montarQuery({}), '');
  assert.equal(util.montarQuery(null), '');
  assert.equal(util.montarQuery({ a: 1, b: '', c: null, d: undefined, e: false }), '?a=1');
  assert.equal(util.montarQuery({ q: 'pão & café', letra: ['A', 'B'] }), '?q=p%C3%A3o%20%26%20caf%C3%A9&letra=A%2CB');
  assert.equal(util.montarQuery({ n: 0 }), '?n=0');
  assert.equal(util.montarQuery({ lista: [] }), '');
});

test('plural', () => {
  assert.equal(`1 ${util.plural(1, 'negócio', 'negócios')}`, '1 negócio');
  assert.equal(`0 ${util.plural(0, 'negócio', 'negócios')}`, '0 negócios');
  assert.equal(`5 ${util.plural(5, 'negócio', 'negócios')}`, '5 negócios');
});

test('abaDoHash cai em buscar quando o endereço não é de uma aba', () => {
  assert.equal(util.abaDoHash('#/leads'), 'leads');
  assert.equal(util.abaDoHash('#/oferta'), 'oferta');
  for (const ruim of ['', '#', '#/', '#/nada', '#/Leads', '#/leads/1', 'leads', undefined, null]) {
    assert.equal(util.abaDoHash(ruim), 'buscar', String(ruim));
  }
  assert.equal(util.hashDaAba('leads'), '#/leads');
});

test('abaVizinha: setas, Home, End, e dá a volta', () => {
  const abas = ['buscar', 'leads', 'oferta'];
  assert.equal(util.abaVizinha('buscar', 'ArrowRight', abas), 'leads');
  assert.equal(util.abaVizinha('oferta', 'ArrowRight', abas), 'buscar');
  assert.equal(util.abaVizinha('buscar', 'ArrowLeft', abas), 'oferta');
  assert.equal(util.abaVizinha('leads', 'Home', abas), 'buscar');
  assert.equal(util.abaVizinha('leads', 'End', abas), 'oferta');
  assert.equal(util.abaVizinha('leads', 'a', abas), null);
  assert.equal(util.abaVizinha('leads', 'Enter', abas), null);
  assert.equal(util.abaVizinha('buscar', 'ArrowRight', ['oferta']), 'oferta');  // só uma habilitada
});

test('situacaoDoPerfil e abasHabilitadas', () => {
  assert.equal(util.situacaoDoPerfil(null), 'desconhecida');
  assert.equal(util.situacaoDoPerfil({}), 'desconhecida');
  assert.equal(util.situacaoDoPerfil({ perfil: { existe: false, valido: false } }), 'ausente');
  assert.equal(util.situacaoDoPerfil({ perfil: { existe: true, valido: false } }), 'invalido');
  assert.equal(util.situacaoDoPerfil({ perfil: { existe: true, valido: true } }), 'ok');
  assert.deepEqual(util.abasHabilitadas('ok'), ['buscar', 'leads', 'oferta']);
  assert.deepEqual(util.abasHabilitadas('invalido'), ['oferta']);
  assert.deepEqual(util.abasHabilitadas('ausente'), []);
  assert.deepEqual(util.abasHabilitadas('desconhecida'), []);
});

test('temaAlternado segue o sistema quando nada foi escolhido', () => {
  assert.equal(util.temaAlternado(null, false), 'dark');
  assert.equal(util.temaAlternado(null, true), 'light');
  assert.equal(util.temaAlternado('light', true), 'dark');
  assert.equal(util.temaAlternado('dark', false), 'light');
});

test('classificarFalha e textoDaFalha', () => {
  const casos = { 0: 'rede', 401: 'token', 403: 'recusado', 404: 'naoencontrado', 409: 'conflito',
    503: 'ocupado', 500: 'servidor', 502: 'servidor', 400: 'pedido', 422: 'pedido', 415: 'pedido' };
  for (const [status, tipo] of Object.entries(casos)) assert.equal(util.classificarFalha(Number(status)), tipo, status);
  assert.equal(util.classificarFalha(undefined), 'rede');
  assert.match(util.textoDaFalha('rede').titulo, /parou de responder/);
  assert.match(util.textoDaFalha('token').texto, /Recarregue/);
  assert.equal(util.textoDaFalha('pedido', 'Falta a cidade.').texto, 'Falta a cidade.');
  assert.match(util.textoDaFalha('pedido').texto, /Tente de novo/);
  for (const t of ['rede', 'token', 'servidor', 'recusado', 'pedido']) {
    const { titulo, texto } = util.textoDaFalha(t, 'x');
    assert.ok(!titulo.includes('—') && !texto.includes('—'));
  }
});

// ---------- api.js, com fetch e document de mentira

function simular(resposta, { token = 'tok-123' } = {}) {
  const chamadas = [];
  globalThis.document = { querySelector: () => ({ content: token }) };
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push({ url, opcoes });
    if (resposta instanceof Error) throw resposta;
    return { ok: resposta.status < 400, status: resposta.status, text: async () => resposta.corpo };
  };
  return chamadas;
}

test('GET não leva token nem corpo e monta a query', async () => {
  const chamadas = simular({ status: 200, corpo: '{"ok":true}' });
  const dados = await api.ler('/api/leads', { letra: 'A', q: '' });
  assert.deepEqual(dados, { ok: true });
  assert.equal(chamadas[0].url, '/api/leads?letra=A');
  assert.equal(chamadas[0].opcoes.method, 'GET');
  assert.equal(chamadas[0].opcoes.headers['X-Token'], undefined);
  assert.equal(chamadas[0].opcoes.body, undefined);
});

test('escrita leva X-Token, JSON e o corpo, com aspas intactas', async () => {
  const chamadas = simular({ status: 200, corpo: '{"id":1}' });
  await api.escrever('PATCH', '/api/leads/1', { anotacao: 'ligar "terça"' });
  const { opcoes } = chamadas[0];
  assert.equal(opcoes.method, 'PATCH');
  assert.equal(opcoes.headers['X-Token'], 'tok-123');
  assert.equal(opcoes.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(opcoes.body), { anotacao: 'ligar "terça"' });
  assert.equal(opcoes.credentials, 'same-origin');
});

test('escrita sem corpo manda objeto vazio', async () => {
  const chamadas = simular({ status: 200, corpo: '{}' });
  await api.escrever('POST', '/api/leads/reavaliar');
  assert.equal(chamadas[0].opcoes.body, '{}');
});

test('401 vira erro de token, com a mensagem do servidor', async () => {
  simular({ status: 401, corpo: '{"erro":"Falta a permissão."}' });
  await assert.rejects(api.escrever('POST', '/api/buscas', {}), (e) => {
    assert.ok(e instanceof api.ErroApi);
    assert.equal(e.tipo, 'token');
    assert.equal(e.status, 401);
    assert.equal(e.message, 'Falta a permissão.');
    return true;
  });
});

test('422 e 409 carregam a lista de erros', async () => {
  simular({ status: 422, corpo: '{"erro":"O perfil tem problemas.","erros":["a","b"]}' });
  await assert.rejects(api.escrever('PUT', '/api/perfil', {}), (e) => {
    assert.equal(e.tipo, 'pedido');
    assert.deepEqual(e.erros, ['a', 'b']);
    return true;
  });
  simular({ status: 409, corpo: '{"erro":"Já existe uma busca.","busca_em_andamento":7}' });
  await assert.rejects(api.escrever('POST', '/api/buscas', {}), (e) => {
    assert.equal(e.tipo, 'conflito');
    assert.equal(e.extra.busca_em_andamento, 7);
    return true;
  });
});

test('servidor fora do ar vira erro de rede', async () => {
  simular(new TypeError('Failed to fetch'));
  await assert.rejects(api.ler('/api/estado'), (e) => e.tipo === 'rede' && e.status === 0);
});

test('resposta de erro que não é JSON não quebra', async () => {
  simular({ status: 500, corpo: '<html>boom</html>' });
  await assert.rejects(api.ler('/api/estado'), (e) => e.tipo === 'servidor' && /Veja a janela/.test(e.message));
});

test('cancelamento (AbortError) passa direto, sem virar erro de rede', async () => {
  const abortado = Object.assign(new Error('abortado'), { name: 'AbortError' });
  simular(abortado);
  await assert.rejects(api.ler('/api/estado'), (e) => e.name === 'AbortError');
});

test('urlDownload só monta o endereço', () => {
  assert.equal(api.urlDownload('/api/exportar', { formato: 'xlsx', letra: 'A' }), '/api/exportar?formato=xlsx&letra=A');
});

test('seguidor: só a última chamada vale', async () => {
  const seguir = api.seguidor();
  let solta1;
  const primeira = seguir((sinal) => new Promise((resolve, reject) => {
    solta1 = resolve;
    sinal.addEventListener('abort', () => reject(Object.assign(new Error('x'), { name: 'AbortError' })));
  }));
  const segunda = seguir(async () => 'nova');
  assert.equal(await primeira, api.ABANDONADA);
  assert.equal(await segunda, 'nova');
  solta1('velha');  // resposta atrasada da primeira: ninguém mais ouve
});

test('seguidor: resposta velha que chega depois é descartada mesmo sem cancelar', async () => {
  const seguir = api.seguidor();
  let solta;
  const velha = seguir(() => new Promise((resolve) => { solta = resolve; }));
  const nova = seguir(async () => 'nova');
  solta('velha');
  assert.equal(await velha, api.ABANDONADA);
  assert.equal(await nova, 'nova');
});

test('seguidor repassa erros de verdade', async () => {
  const seguir = api.seguidor();
  await assert.rejects(seguir(async () => { throw new Error('falhou'); }), /falhou/);
});
