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
  await assert.rejects(api.ler('/api/estado'), (e) => e.tipo === 'rede' && e.status === 0 && /parou de responder\. Confira/.test(e.message));
});

test('resposta de erro que não é JSON não quebra', async () => {
  simular({ status: 500, corpo: '<html>boom</html>' });
  await assert.rejects(api.ler('/api/estado'), (e) => e.tipo === 'servidor' && /Olhe a janela escura/.test(e.message));
});

test('cancelamento (AbortError) passa direto, sem virar erro de rede', async () => {
  const abortado = Object.assign(new Error('abortado'), { name: 'AbortError' });
  simular(abortado);
  await assert.rejects(api.ler('/api/estado'), (e) => e.name === 'AbortError');
});

test('baixar leva o token, monta a query e devolve o arquivo com o nome seguro', async () => {
  const chamadas = [];
  globalThis.document = { querySelector: () => ({ content: 'tok-123' }) };
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push({ url, opcoes });
    return {
      ok: true, status: 200, blob: async () => ({ tamanho: 5 }),
      headers: { get: (n) => (n === 'Content-Disposition' ? 'attachment; filename="leads.xlsx"' : null) },
    };
  };
  const { blob, nome } = await api.baixar('/api/exportar', { formato: 'xlsx', letra: 'A', q: '' });
  assert.equal(chamadas[0].url, '/api/exportar?formato=xlsx&letra=A');
  assert.equal(chamadas[0].opcoes.method, 'GET');
  assert.equal(chamadas[0].opcoes.headers['X-Token'], 'tok-123');
  assert.equal(nome, 'leads.xlsx');
  assert.deepEqual(blob, { tamanho: 5 });
});

test('baixar: 401 vira erro de token e nenhum arquivo sai', async () => {
  globalThis.document = { querySelector: () => ({ content: 'velho' }) };
  globalThis.fetch = async () => ({ ok: false, status: 401, text: async () => '{"erro":"Falta a permissão."}', headers: { get: () => null } });
  await assert.rejects(api.baixar('/api/exportar', { formato: 'csv' }), (e) => e.tipo === 'token' && e.status === 401);
});

test('baixar: servidor fora do ar vira erro de rede', async () => {
  globalThis.document = { querySelector: () => ({ content: 'x' }) };
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(api.baixar('/api/exportar', {}), (e) => e.tipo === 'rede');
});

test('api.js não tem mais urlDownload (download sem token)', () => {
  assert.equal(api.urlDownload, undefined);
  assert.equal(typeof api.baixar, 'function');
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

// ---------- Leads: funções puras

test('nomeDoArquivo só aceita nome simples', () => {
  assert.equal(util.nomeDoArquivo('attachment; filename="leads.xlsx"'), 'leads.xlsx');
  assert.equal(util.nomeDoArquivo('attachment; filename=leads.csv'), 'leads.csv');
  for (const ruim of ['attachment; filename="../../x.exe"', 'attachment; filename="a/b.csv"', 'attachment; filename="a b.csv"', '', null, undefined, 'attachment']) {
    assert.equal(util.nomeDoArquivo(ruim), 'leads', String(ruim));
  }
  assert.equal(util.nomeDoArquivo('', 'padrao.csv'), 'padrao.csv');
});

test('linkWhatsApp: só número no formato 55 + DDD + celular, só dígitos', () => {
  const ok = util.linkWhatsApp('5561999990001', 'Oi, tudo bem?');
  assert.equal(ok.url, 'https://wa.me/5561999990001?text=Oi%2C%20tudo%20bem%3F');
  assert.equal(ok.comMensagem, true);
  assert.equal(util.linkWhatsApp('5561999990001', '').url, 'https://wa.me/5561999990001');
  assert.equal(util.linkWhatsApp('5561999990001', '   ').comMensagem, false);
  const ruins = [
    '', null, undefined, 5561999990001, '556133330001', '55619999900011', '5561899990001', '5501999990001',
    '5561999990001"><script>', 'https://evil.invalid/5561999990001', '+5561999990001', '55 61 99999-0001',
    '5561\n999990001', '5561999990001 ', ' 5561999990001', '55619999900a1', '1234',
  ];
  for (const r of ruins) assert.equal(util.linkWhatsApp(r, 'oi'), null, String(r));
});

test('linkWhatsApp: a mensagem é codificada e nunca vira parte do endereço', () => {
  const l = util.linkWhatsApp('5561999990001', 'a&b=c#d?e "f" <g>');
  assert.equal(new URL(l.url).hostname, 'wa.me');
  assert.equal(new URL(l.url).pathname, '/5561999990001');
  assert.equal(new URL(l.url).searchParams.get('text'), 'a&b=c#d?e "f" <g>');
  assert.equal([...new URL(l.url).searchParams.keys()].length, 1);
});

test('linkWhatsApp: mensagem grande demais abre a conversa sem texto', () => {
  const l = util.linkWhatsApp('5561999990001', 'ã'.repeat(400));
  assert.equal(l.url, 'https://wa.me/5561999990001');
  assert.equal(l.comMensagem, false);
});

test('tipoDeSite', () => {
  assert.equal(util.tipoDeSite(''), 'nenhum');
  assert.equal(util.tipoDeSite(null), 'nenhum');
  assert.equal(util.tipoDeSite('https://www.instagram.com/x'), 'rede');
  assert.equal(util.tipoDeSite('instagram.com/x'), 'rede');
  assert.equal(util.tipoDeSite('https://m.facebook.com/x'), 'rede');
  assert.equal(util.tipoDeSite('https://meusite.invalid'), 'tem');
  assert.equal(util.tipoDeSite('https://naoinstagram.com.invalid'), 'tem');
  assert.equal(util.tipoDeSite('https://exemplo.invalid/instagram.com'), 'tem');
});

test('urlSegura: só http e https', () => {
  assert.equal(util.urlSegura('https://a.invalid/x?y=1'), 'https://a.invalid/x?y=1');
  assert.equal(util.urlSegura(' http://a.invalid '), 'http://a.invalid/');
  for (const ruim of ['javascript:alert(1)', 'data:text/html,x', 'file:///c:/x', 'ftp://a.invalid', 'www.sem-esquema.com', '', null, 'https://', 'https://' + 'a'.repeat(2100)]) {
    assert.equal(util.urlSegura(ruim), null, String(ruim).slice(0, 30));
  }
});

test('avisoDeConformidade', () => {
  const aviso = (r) => util.avisoDeConformidade({ conformidade: { restricoes: r } });
  for (const nenhum of ['nao', 'Não', 'NAO', ' não ', '', undefined]) assert.equal(aviso(nenhum), null, String(nenhum));
  assert.equal(util.avisoDeConformidade({}), null);
  assert.equal(util.avisoDeConformidade(null), null);
  assert.deepEqual(aviso('nao sei'), { tipo: 'incerto', detalhe: '' });
  assert.deepEqual(aviso('Não sei'), { tipo: 'incerto', detalhe: '' });
  assert.deepEqual(aviso('nao_sei'), { tipo: 'incerto', detalhe: '' });
  assert.deepEqual(aviso('sim: advocacia (OAB)'), { tipo: 'regulado', detalhe: 'advocacia (OAB)' });
  assert.deepEqual(aviso('Sim'), { tipo: 'regulado', detalhe: '' });
  assert.deepEqual(aviso('medicina, CFM'), { tipo: 'regulado', detalhe: 'medicina, CFM' });
});

test('formatarNota, rotuloDoStatus e resumoDaLista', () => {
  assert.equal(util.formatarNota(4.8), '4,8');
  assert.equal(util.formatarNota('4.5'), '4,5');
  assert.equal(util.formatarNota(5), '5');
  assert.equal(util.formatarNota(null), '-');
  assert.equal(util.formatarNota(undefined), '-');
  assert.equal(util.rotuloDoStatus('respondeu'), 'Respondeu');
  assert.equal(util.rotuloDoStatus('qualquer'), 'Novo');
  assert.equal(util.resumoDaLista(0, 0), 'Nenhum lead');
  assert.equal(util.resumoDaLista(1, 1), '1 lead');
  assert.equal(util.resumoDaLista(12, 12), '12 leads');
  assert.equal(util.resumoDaLista(100, 650), 'Mostrando 100 de 650 leads');
});

test('lista grande: quantos faltam e como pedir a próxima parte', () => {
  assert.equal(util.PAGINA_LEADS, 100);
  assert.equal(util.quantosFaltam(100, 650), 100);
  assert.equal(util.quantosFaltam(600, 650), 50);
  assert.equal(util.quantosFaltam(650, 650), 0);
  assert.equal(util.quantosFaltam(700, 650), 0);
  assert.equal(util.quantosFaltam(0, 0), 0);
});

test('situacaoDaLista: vazia sem buscas, sem resultado com filtro, tudo excluído', () => {
  const padrao = { ...util.FILTROS_PADRAO };
  assert.equal(util.situacaoDaLista({ total: 5, filtros: padrao, buscasFeitas: true }), 'lista');
  assert.equal(util.situacaoDaLista({ total: 0, filtros: padrao, buscasFeitas: false }), 'nenhuma-busca');
  assert.equal(util.situacaoDaLista({ total: 0, filtros: padrao, buscasFeitas: true }), 'sem-leads-na-lista');
  assert.equal(util.situacaoDaLista({ total: 0, filtros: { ...padrao, letra: 'A' }, buscasFeitas: true }), 'sem-resultado');
  assert.equal(util.situacaoDaLista({ total: 0, filtros: { ...padrao, q: 'xis' }, buscasFeitas: false }), 'sem-resultado');
  assert.equal(util.situacaoDaLista({ total: 0, filtros: { ...padrao, excluidos: 'todos' }, buscasFeitas: true }), 'sem-resultado');
});

test('filtros rápidos Sem site e Com celular contam como filtro ligado quando valem 1', () => {
  assert.deepEqual(util.filtrosAtivos({ ...util.FILTROS_PADRAO, sem_site: '1' }), ['sem_site']);
  assert.deepEqual(util.filtrosAtivos({ ...util.FILTROS_PADRAO, sem_site: '1', celular: '1' }), ['sem_site', 'celular']);
  assert.deepEqual(util.filtrosAtivos({ ...util.FILTROS_PADRAO, celular: '' }), []);
  assert.equal(util.situacaoDaLista({ total: 0, filtros: { ...util.FILTROS_PADRAO, sem_site: '1' }, buscasFeitas: true }), 'sem-resultado');
  assert.equal(util.montarQuery({ sem_site: '1', celular: '', letra: 'A' }), '?sem_site=1&letra=A');
});

test('filtrosAtivos só conta o que difere do padrão', () => {
  assert.deepEqual(util.filtrosAtivos({ ...util.FILTROS_PADRAO }), []);
  assert.deepEqual(util.filtrosAtivos({ ...util.FILTROS_PADRAO, letra: 'B', busca: 3 }), ['letra', 'busca']);
  assert.deepEqual(util.filtrosAtivos(null), []);
});
