// Tela Buscar: funções puras e peças de desenho. Dado malicioso vira texto, resultado zero não é sucesso,
// não existe botão de cancelar e os textos não prometem quantidade.
import test from 'node:test';
import assert from 'node:assert/strict';
import { elementos, tags, textos, textoTodo, botoes } from './dom_falso.mjs';

const util = await import('../../kit/painel/util.js');
const buscar = await import('../../kit/painel/tela-buscar.js');

const MALICIOSO = '<img src=x onerror=alert(1)>';
const UFS = ['AC', 'DF', 'GO', 'SP', 'RJ'];
const PERIGOSAS = ['IMG', 'SCRIPT', 'SVG', 'IFRAME', 'B', 'STYLE'];

const busca = (extra = {}) => ({
  id: 7, categoria: 'padaria', cidade: 'Sobradinho', uf: 'DF', tamanho: 'media', status: 'ok',
  criada_em: '2026-10-30T10:00:00', terminou_em: '2026-10-30T10:05:20', total_leads: 88, novos: 70, ja_existiam: 18,
  fora_da_lista: 9, erro: null, erro_tipo: null, etapa: null, segundos: null, ponto: null, pontos: 5,
  tempo_estimado: 'cerca de 5 a 6 minutos', ...extra,
});

// ---------- funções puras

test('parseRegiao: Cidade-UF em vários jeitos, e o que não é cidade devolve null', () => {
  assert.deepEqual(util.parseRegiao('Brasília-DF', UFS), { cidade: 'Brasília', uf: 'DF' });
  assert.deepEqual(util.parseRegiao('Brasília - DF', UFS), { cidade: 'Brasília', uf: 'DF' });
  assert.deepEqual(util.parseRegiao('Goiânia, go', UFS), { cidade: 'Goiânia', uf: 'GO' });
  assert.deepEqual(util.parseRegiao('Rio/RJ', UFS), { cidade: 'Rio', uf: 'RJ' });
  assert.deepEqual(util.parseRegiao('Embu-Guaçu - SP', UFS), { cidade: 'Embu-Guaçu', uf: 'SP' });
  for (const nao of ['Todo o Brasil', 'Brasília', '', null, undefined, '-DF', 'Cidade-ZZ', 'x'.repeat(100) + '-DF']) {
    assert.equal(util.parseRegiao(nao, UFS), null, String(nao).slice(0, 20));
  }
});

test('sugestões vêm do perfil, sem repetir, e aceitam perfil incompleto', () => {
  const perfil = { cliente: { tipos: ['padaria', 'Padaria', ' academia ', '', 'x'.repeat(90), 'restaurante'], regioes: ['Brasília-DF', 'brasília - df', 'Todo o Brasil', 'Sobradinho-DF'] } };
  assert.deepEqual(util.sugestoesDeCategoria(perfil), ['padaria', 'academia', 'restaurante']);
  assert.deepEqual(util.sugestoesDeCidade(perfil, UFS).map((c) => c.rotulo), ['Brasília-DF', 'Sobradinho-DF']);
  for (const vazio of [null, {}, { cliente: {} }, { cliente: { tipos: 'x', regioes: null } }]) {
    assert.deepEqual(util.sugestoesDeCategoria(vazio), []);
    assert.deepEqual(util.sugestoesDeCidade(vazio, UFS), []);
  }
});

test('validarBusca: campo vazio tem mensagem própria, e o texto livre é aceito', () => {
  assert.deepEqual(util.validarBusca({ categoria: 'padaria', cidade: 'Sobradinho', uf: 'DF' }, UFS), {});
  assert.deepEqual(util.validarBusca({ categoria: 'qualquer coisa que eu queira', cidade: ' X ', uf: 'GO' }, UFS), {});
  const todos = util.validarBusca({ categoria: '  ', cidade: '', uf: '' }, UFS);
  assert.deepEqual(Object.keys(todos), ['categoria', 'cidade', 'uf']);
  assert.match(todos.categoria, /Escreva o tipo de negócio/);
  assert.match(todos.cidade, /nome da cidade/);
  assert.match(todos.uf, /Escolha o estado/);
  assert.ok(util.validarBusca({ categoria: 'x'.repeat(81), cidade: 'A', uf: 'DF' }, UFS).categoria.includes('grande demais'));
  assert.ok(util.validarBusca({ categoria: 'a', cidade: 'x'.repeat(81), uf: 'DF' }, UFS).cidade.includes('grande demais'));
  assert.ok(util.validarBusca({ categoria: 'a', cidade: 'b', uf: 'ZZ' }, UFS).uf);
});

test('formatarDuracao, duracaoDaBusca e quandoFoi', () => {
  assert.equal(util.formatarDuracao(0), '0 s');
  assert.equal(util.formatarDuracao(45), '45 s');
  assert.equal(util.formatarDuracao(60), '1 min');
  assert.equal(util.formatarDuracao(332), '5 min 32 s');
  assert.equal(util.formatarDuracao(3720), '1 h 2 min');
  assert.equal(util.formatarDuracao(null), '0 s');
  assert.equal(util.duracaoDaBusca(busca()), 320);
  assert.equal(util.duracaoDaBusca(busca({ terminou_em: null })), null);
  assert.equal(util.duracaoDaBusca(busca({ terminou_em: '2026-10-30T09:00:00' })), null);
  assert.equal(util.duracaoDaBusca(null), null);
  const agora = new Date(2026, 9, 30, 15, 0, 0);
  assert.equal(util.quandoFoi(new Date(2026, 9, 30, 14, 32).toISOString(), agora), 'hoje às 14:32');
  assert.equal(util.quandoFoi(new Date(2026, 9, 29, 9, 5).toISOString(), agora), 'ontem às 09:05');
  assert.equal(util.quandoFoi(new Date(2026, 9, 28, 16, 40).toISOString(), agora), '28/10 às 16:40');
  assert.equal(util.quandoFoi('lixo', agora), '');
});

test('etapas e porcentagem: só mostra número quando dá para saber', () => {
  assert.equal(util.indiceDaEtapa('Achando a cidade no mapa'), 0);
  assert.equal(util.indiceDaEtapa('Enviando a busca ao motor (ponto 2 de 5)'), 1);
  assert.equal(util.indiceDaEtapa('Esperando o motor (ponto 2 de 5)'), 2);
  assert.equal(util.indiceDaEtapa('Pausa entre os pontos (ponto 3 de 5)'), 2);
  assert.equal(util.indiceDaEtapa('Lendo os resultados'), 3);
  assert.equal(util.indiceDaEtapa('Calculando as notas'), 4);
  assert.equal(util.indiceDaEtapa(null), -1);
  assert.equal(util.percentualDaBusca({ pontos: 5, ponto: 1, etapa: 'Esperando o motor' }), 0);
  assert.equal(util.percentualDaBusca({ pontos: 5, ponto: 3, etapa: 'Esperando o motor' }), 40);
  assert.equal(util.percentualDaBusca({ pontos: 5, ponto: 5, etapa: 'Calculando as notas' }), 100);
  assert.equal(util.percentualDaBusca({ pontos: 1, ponto: 1, etapa: 'Esperando o motor' }), null);  // uma busca só: sem número inventado
  assert.equal(util.percentualDaBusca(null), null);
});

test('resumo: sucesso traz novos, já existiam e fora da lista', () => {
  const r = util.resumoDaBusca(busca());
  assert.equal(r.tipo, 'sucesso');
  assert.equal(r.titulo, 'Busca concluída: 88 negócios encontrados');
  assert.deepEqual(r.linhas, [
    '70 negócios novos, que ainda não estavam no kit.',
    '18 já existiam de buscas anteriores.',
    '9 ficaram fora da lista pelas exclusões do seu perfil (por exemplo, sem telefone ou possível rede).',
  ]);
  assert.equal(r.tempo, 'A busca levou 5 min 20 s.');
  assert.equal(r.temLeads, true);
});

test('resumo: singular, nenhum novo e nenhum fora da lista', () => {
  const um = util.resumoDaBusca(busca({ total_leads: 1, novos: 1, ja_existiam: 0, fora_da_lista: 1 }));
  assert.equal(um.titulo, 'Busca concluída: 1 negócio encontrado');
  assert.deepEqual(um.linhas, ['1 negócio novo, que ainda não estava no kit.'.replace('estava', 'estavam'), '0 já existiam de buscas anteriores.', '1 ficou fora da lista pelas exclusões do seu perfil (por exemplo, sem telefone ou possível rede).']);
  const nenhumNovo = util.resumoDaBusca(busca({ total_leads: 12, novos: 0, ja_existiam: 12, fora_da_lista: 0 }));
  assert.ok(nenhumNovo.linhas.includes('Nenhum ficou fora da lista pelas exclusões do seu perfil.'));
  assert.ok(nenhumNovo.linhas.includes('Nenhum negócio novo: todos já estavam no kit.'));
});

test('resumo: resultado ZERO nunca é sucesso e explica o que tentar', () => {
  const r = util.resumoDaBusca(busca({ total_leads: 0, novos: 0, ja_existiam: 0, fora_da_lista: 0 }));
  assert.equal(r.tipo, 'vazio');
  assert.equal(r.titulo, 'Nenhum negócio encontrado');
  assert.doesNotMatch(r.titulo, /conclu[ií]d|sucesso/i);
  assert.doesNotMatch(r.texto.replace('Isto não é um sucesso', ''), /conclu[ií]d|sucesso/i);  // só a negação é permitida
  assert.match(r.texto, /Isto não é um sucesso/);
  assert.match(r.texto, /cidade, o termo da busca ou uma mudança no Google/);
  assert.equal(r.temLeads, false);
  assert.equal(r.linhas.length, 0);
  assert.ok(r.dicas.length >= 4);
  const dicas = r.dicas.join(' ');
  assert.match(dicas, /nome da cidade e o estado/);
  assert.match(dicas, /outro termo/);
  assert.match(dicas, /daqui a alguns minutos/);
  assert.match(dicas, /o Google pode ter mudado/);   // parte do plano de manutenção contra mudanças do Google
  assert.match(dicas, /atualização/);
  const semNumero = util.resumoDaBusca(busca({ total_leads: null }));  // busca antiga, sem contagens
  assert.equal(semNumero.tipo, 'vazio');
});

test('resumo: busca antiga sem contagens mostra só o total, sem inventar números', () => {
  const r = util.resumoDaBusca(busca({ novos: null, ja_existiam: null, fora_da_lista: null, total_leads: 16 }));
  assert.equal(r.tipo, 'sucesso');
  assert.deepEqual(r.linhas, []);
});

test('erros da busca: cada tipo tem título e orientação próprios', () => {
  const tipos = ['cidade', 'servico_de_mapas', 'motor', 'formato', 'parcial', 'interrompida', 'inesperado', undefined, null, 'qualquer'];
  const titulos = new Set();
  for (const tipo of tipos) {
    const e = util.textoDoErroDaBusca({ erro_tipo: tipo });
    assert.ok(e.titulo && e.dica);
    assert.ok(!(e.titulo + e.dica).includes('—'));
    titulos.add(e.titulo);
  }
  assert.equal(titulos.size, 7);  // seis tipos conhecidos + o genérico
  assert.match(util.textoDoErroDaBusca({ erro_tipo: 'cidade' }).dica, /Confira o nome da cidade e o estado/);
  assert.match(util.textoDoErroDaBusca({ erro_tipo: 'formato' }).dica, /atualização/);
  assert.match(util.textoDoErroDaBusca({ erro_tipo: 'parcial' }).dica, /foi salvo e está em Leads/);
});

test('resumo de erro: parcial mostra o que foi salvo, erro comum não mostra contagem', () => {
  const parcial = util.resumoDaBusca(busca({ status: 'erro', erro_tipo: 'parcial', total_leads: 36, novos: 30, ja_existiam: 6, fora_da_lista: 3, erro: 'A busca parou no ponto 3 de 5.' }));
  assert.equal(parcial.tipo, 'parcial');
  assert.equal(parcial.temLeads, true);
  assert.equal(parcial.linhas.length, 3);
  assert.equal(parcial.detalhe, 'A busca parou no ponto 3 de 5.');
  const erro = util.resumoDaBusca(busca({ status: 'erro', erro_tipo: 'cidade', total_leads: 0, erro: 'Não achei a cidade X-DF.' }));
  assert.equal(erro.tipo, 'erro');
  assert.deepEqual(erro.linhas, []);
  assert.equal(erro.temLeads, false);
});

// ---------- textos da tela

test('texto do resultado: o Google varia e o kit não promete quantidade', () => {
  const t = buscar.TEXTO_RESULTADO_VARIA;
  assert.match(t, /O Google muda de uma busca para outra/);
  assert.match(t, /depende da cidade e do tipo de negócio/);
  assert.match(t, /não promete uma quantidade/);
});

test('nenhum texto da tela promete ou cita os números medidos (65, 88, 16, 20)', () => {
  const todos = [
    buscar.TEXTO_RESULTADO_VARIA, buscar.TEXTO_SEM_CANCELAR, buscar.TEXTO_AVISO_IP, buscar.TEXTO_USO_RESPONSAVEL.texto,
    ...buscar.TEXTO_PRIVACIDADE.itens, ...util.DICAS_DE_RESULTADO_ZERO,
    ...['cidade', 'servico_de_mapas', 'motor', 'formato', 'parcial', 'interrompida', 'x'].flatMap((t) => Object.values(util.textoDoErroDaBusca({ erro_tipo: t }))),
  ].join(' ');
  assert.doesNotMatch(todos, /\b(65|88|16|20|garant\w*)\b/i);
  assert.doesNotMatch(todos, /—/);
});

test('privacidade: diz o que sai do computador, e só isso', () => {
  const t = buscar.TEXTO_PRIVACIDADE;
  assert.equal(t.titulo, 'O que sai do seu computador');
  assert.equal(t.itens.length, 3);
  assert.match(t.itens[0], /nome da cidade e o estado/);
  assert.match(t.itens[0], /OpenStreetMap \(Nominatim\)/);
  assert.match(t.itens[1], /roda no seu computador e consulta o Google Maps pela sua conexão/);
  assert.match(t.itens[2], /ficam só no seu computador/);
});

test('uso responsável: termos do Google, LGPD e envio manual', () => {
  const t = buscar.TEXTO_USO_RESPONSAVEL.texto;
  assert.match(t, /termos de uso do Google/);
  assert.match(t, /LGPD/);
  assert.match(t, /O envio é sempre manual/);
  assert.doesNotMatch(t, /protege|garant|seguro/i);
});

test('sem cancelar: o texto diz que não dá, sem prometer nada além', () => {
  assert.match(buscar.TEXTO_SEM_CANCELAR, /não tem como cancelar uma busca/);
  assert.match(buscar.TEXTO_SEM_CANCELAR, /desde que a janela do kit fique aberta/);
  assert.match(buscar.TEXTO_SEM_CANCELAR, /Só uma busca roda por vez/);
});

// ---------- peças de desenho

test('progresso: atualiza no lugar, mostra o ponto e não tem botão de cancelar', () => {
  const p = buscar.criarProgresso(busca({ status: 'working', etapa: 'Esperando o motor (ponto 2 de 5)', segundos: 75, ponto: 2 }));
  const no = p.no;
  assert.equal(botoes(no).length, 0);  // nenhum botão: não existe cancelar
  assert.ok(textoTodo(no).includes('Buscando padaria em Sobradinho-DF'));
  assert.ok(textoTodo(no).includes('1 min 15 s'));
  assert.ok(textoTodo(no).includes('2 de 5'));
  assert.ok(textoTodo(no).includes('Estimativa: cerca de 5 a 6 minutos (pode variar)'));
  assert.ok(textoTodo(no).includes('não tem como cancelar uma busca'));
  const barra = elementos(no).find((n) => n.attributes.role === 'progressbar');
  assert.equal(barra.attributes['aria-valuenow'], '20');
  assert.ok(!barra.className.includes('indeterminada'));
  const filhosAntes = no.children.length;
  p.atualizar(busca({ status: 'working', etapa: 'Esperando o motor (ponto 4 de 5)', segundos: 200, ponto: 4 }));
  assert.equal(no.children.length, filhosAntes);  // mesmo cartão, atualizado no lugar
  assert.equal(barra.attributes['aria-valuenow'], '60');
  assert.ok(textoTodo(no).includes('3 min 20 s'));
  assert.ok(textoTodo(no).includes('4 de 5'));
  const passos = elementos(no).filter((n) => n.tagName === 'LI');
  assert.deepEqual(passos.map((li) => li.className), ['feito', 'feito', 'on', '', '']);
});

test('progresso de busca rápida: barra sem fim definido, sem número inventado', () => {
  const p = buscar.criarProgresso(busca({ tamanho: 'rapida', pontos: 1, ponto: 1, status: 'working', etapa: 'Esperando o motor', segundos: 20 }));
  const barra = elementos(p.no).find((n) => n.attributes.role === 'progressbar');
  assert.ok(barra.className.includes('indeterminada'));
  assert.equal(barra.attributes['aria-valuenow'], undefined);
  assert.ok(!textoTodo(p.no).includes('Ponto:') || p.no.children.length);  // sem "ponto 1 de 1"
  assert.ok(![...textoTodo(p.no).matchAll(/1 de 1/g)].length);
});

test('progresso: quando o kit não responde, avisa sem desistir', () => {
  const p = buscar.criarProgresso(busca({ status: 'working', etapa: 'Esperando o motor', ponto: 1 }));
  const aviso = elementos(p.no).find((n) => n.attributes.role === 'alert');
  assert.equal(aviso.hidden, true);
  p.atualizar(busca({ status: 'working', etapa: 'Esperando o motor', ponto: 1 }), { semResposta: true });
  assert.equal(aviso.hidden, false);
  assert.match(aviso.textContent, /Continuo tentando/);
});

test('progresso: dado malicioso na busca vira só texto', () => {
  const p = buscar.criarProgresso(busca({ categoria: MALICIOSO, cidade: '<script>alert(1)</script>', status: 'working', etapa: MALICIOSO, ponto: 1 }));
  for (const tag of PERIGOSAS) assert.ok(!tags(p.no).includes(tag) || tag === 'B', tag);
  assert.ok(!tags(p.no).includes('IMG'));
  assert.ok(!tags(p.no).includes('SCRIPT'));
  assert.ok(textoTodo(p.no).includes(`Buscando ${MALICIOSO} em <script>alert(1)</script>-DF`));
  assert.ok(textos(p.no).includes(MALICIOSO));
});

test('resumo na tela: sucesso tem os botões certos e chama as ações', () => {
  const chamadas = [];
  const no = buscar.criarResumo(busca(), {
    aoVerLeads: () => chamadas.push('leads'), aoVerTodos: () => chamadas.push('todos'),
    aoOutra: () => chamadas.push('outra'), aoRepetir: () => chamadas.push('repetir'),
  });
  assert.equal(no.dataset.tipo, 'sucesso');
  assert.deepEqual(botoes(no).map((b) => b.textContent), ['Ver os leads desta busca', 'Ver todos os leads', 'Fazer outra busca']);
  for (const b of botoes(no)) b.ouvintes.click[0]();
  assert.deepEqual(chamadas, ['leads', 'todos', 'outra']);
  const texto = textoTodo(no);
  assert.ok(texto.includes('Busca concluída: 88 negócios encontrados'));
  assert.ok(texto.includes('padaria em Sobradinho-DF'));
  assert.ok(texto.includes('Média'));
  assert.ok(texto.includes('70 negócios novos'));
  assert.ok(texto.includes('18 já existiam de buscas anteriores'));
  assert.ok(texto.includes('9 ficaram fora da lista'));
});

test('resumo na tela: zero resultado não parece sucesso', () => {
  const no = buscar.criarResumo(busca({ total_leads: 0, novos: 0, ja_existiam: 0, fora_da_lista: 0 }), { aoVerLeads() {}, aoVerTodos() {}, aoOutra() {}, aoRepetir() {} });
  assert.equal(no.dataset.tipo, 'vazio');
  const texto = textoTodo(no);
  assert.ok(texto.includes('Nenhum negócio encontrado'));
  assert.ok(!/concluída|sucesso!/i.test(texto.replace('Isto não é um sucesso', '')));
  assert.ok(texto.includes('O que você pode tentar'));
  assert.ok(texto.includes('o Google pode ter mudado'));
  assert.deepEqual(botoes(no).map((b) => b.textContent), ['Mudar a busca']);  // sem "Ver os leads" de uma busca vazia
});

test('resumo na tela: erros, parcial e mensagem do kit como texto', () => {
  const erro = buscar.criarResumo(busca({ status: 'erro', erro_tipo: 'cidade', total_leads: 0, erro: `Não achei a cidade ${MALICIOSO}-DF.` }), { aoVerLeads() {}, aoVerTodos() {}, aoOutra() {}, aoRepetir() {} });
  assert.equal(erro.dataset.tipo, 'erro');
  assert.ok(textoTodo(erro).includes('Não achei essa cidade'));
  assert.ok(!tags(erro).includes('IMG'));
  assert.ok(textos(erro).includes(`Mensagem do kit: Não achei a cidade ${MALICIOSO}-DF.`));
  assert.deepEqual(botoes(erro).map((b) => b.textContent), ['Tentar de novo']);
  const parcial = buscar.criarResumo(busca({ status: 'erro', erro_tipo: 'parcial', total_leads: 36, novos: 30, ja_existiam: 6, fora_da_lista: 3 }), { aoVerLeads() {}, aoVerTodos() {}, aoOutra() {}, aoRepetir() {} });
  assert.equal(parcial.dataset.tipo, 'parcial');
  assert.deepEqual(botoes(parcial).map((b) => b.textContent), ['Ver os leads desta busca', 'Ver todos os leads', 'Tentar de novo']);
  assert.ok(textoTodo(parcial).includes('30 negócios novos'));
});

test('resumo na tela: tipo de negócio e cidade maliciosos viram texto', () => {
  const no = buscar.criarResumo(busca({ categoria: MALICIOSO, cidade: '<b>x</b>' }), { aoVerLeads() {}, aoVerTodos() {}, aoOutra() {}, aoRepetir() {} });
  assert.ok(!tags(no).includes('IMG'));
  assert.ok(textoTodo(no).includes(`${MALICIOSO} em <b>x</b>-DF`));
});

test('histórico: só mostra "Ver leads" quando há leads, e dado malicioso vira texto', () => {
  assert.equal(buscar.criarHistorico([], () => {}), null);
  const aberto = [];
  const no = buscar.criarHistorico([
    busca({ id: 3, categoria: MALICIOSO, total_leads: 12 }),
    busca({ id: 2, total_leads: 0 }),
    busca({ id: 1, status: 'erro', erro_tipo: 'cidade', total_leads: 0 }),
  ], (id) => aberto.push(id));
  assert.ok(!tags(no).includes('IMG'));
  assert.ok(textoTodo(no).includes(MALICIOSO));
  assert.ok(textoTodo(no).includes('12 negócios'));
  assert.ok(textoTodo(no).includes('nenhum negócio'));
  assert.ok(textoTodo(no).includes('terminou com erro'));
  assert.equal(botoes(no).length, 1);
  botoes(no)[0].ouvintes.click[0]();
  assert.deepEqual(aberto, [3]);
});

test('motor desligado: cada motivo mostra o que fazer, com onde e como', () => {
  const passos = ['Abra o Docker Desktop pelo menu Iniciar.', 'Clique na barra de endereço, digite powershell e aperte Enter.'];
  const docker = buscar.criarBlocoDoMotor({ estado: 'docker_parado', titulo: 'O Docker está desligado', texto: 'O Docker Desktop está fechado.', passos, comando: 'docker compose up -d' }, () => {});
  assert.ok(textoTodo(docker).includes('O Docker está desligado'));
  assert.ok(textoTodo(docker).includes('Abra o Docker Desktop pelo menu Iniciar'));
  assert.ok(textoTodo(docker).includes('digite powershell e aperte Enter'));
  assert.ok(textoTodo(docker).includes('docker compose up -d'));
  assert.ok(botoes(docker).some((b) => b.textContent === 'Copiar'));
  assert.ok(botoes(docker).some((b) => b.textContent === 'Verificar de novo'));
  const ausente = buscar.criarBlocoDoMotor({ estado: 'docker_ausente', titulo: 'O Docker não foi encontrado', texto: 'x', passos: ['Peça para a sua IA conferir.'], comando: null }, () => {});
  assert.ok(!textoTodo(ausente).includes('docker compose'));
  assert.ok(textoTodo(ausente).includes('Peça para a sua IA conferir'));
  const sem = buscar.criarBlocoDoMotor(null, () => {});  // diagnóstico ainda desconhecido: mensagem geral, com passos
  assert.ok(textoTodo(sem).includes('O motor de busca está desligado'));
  assert.ok(textoTodo(sem).includes('digite powershell e aperte Enter'));
});
