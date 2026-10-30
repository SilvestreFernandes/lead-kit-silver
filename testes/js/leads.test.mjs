// Prova que dado malicioso do Google vira TEXTO na tela de Leads, nunca elemento, atributo ou link.
// Usa um DOM de mentira que, ao contrário de uma string solta, sabe a diferença entre texto e elemento.
import test from 'node:test';
import assert from 'node:assert/strict';

class FakeNode {}
class FakeText extends FakeNode {
  constructor(dados) { super(); this.nodeType = 3; this.dados = String(dados); }
  get textContent() { return this.dados; }
}
class FakeElement extends FakeNode {
  constructor(tag) {
    super();
    this.nodeType = 1;
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.ouvintes = {};
    this.className = '';
  }
  setAttribute(nome, valor) { this.attributes[nome] = String(valor); if (nome === 'class') this.className = String(valor); }
  getAttribute(nome) { return this.attributes[nome] ?? null; }
  removeAttribute(nome) { delete this.attributes[nome]; }
  append(...nos) {
    for (const no of nos) {
      assert.ok(no instanceof FakeNode, 'append recebeu algo que não é um nó: ' + typeof no);
      this.children.push(no);
    }
  }
  addEventListener(tipo, fn) { (this.ouvintes[tipo] ||= []).push(fn); }
  get firstChild() { return this.children[0] ?? null; }
  removeChild(no) { this.children.splice(this.children.indexOf(no), 1); }
  get textContent() { return this.children.map((c) => c.textContent).join(''); }
}
globalThis.Node = FakeNode;
globalThis.document = {
  createElement: (tag) => new FakeElement(tag),
  createTextNode: (texto) => new FakeText(texto),
  getElementById: () => null,
};

const { el } = await import('../../kit/painel/dom.js');
const leads = await import('../../kit/painel/tela-leads.js');

function* percorrer(no) {
  yield no;
  for (const filho of no.children || []) yield* percorrer(filho);
}
const elementos = (no) => [...percorrer(no)].filter((n) => n.nodeType === 1);
const tags = (no) => elementos(no).map((n) => n.tagName);
const textos = (no) => [...percorrer(no)].filter((n) => n.nodeType === 3).map((n) => n.dados);

const MALICIOSO = '<img src=x onerror=alert(1)>';
const PERIGOSAS = ['IMG', 'SCRIPT', 'SVG', 'IFRAME', 'B', 'STYLE', 'OBJECT', 'EMBED'];

function leadMalicioso(extra = {}) {
  return {
    id: 1, nome: MALICIOSO, categoria: '<b>Padaria</b>', endereco: 'Rua <script>alert(1)</script>, 1',
    telefone: '<svg onload=alert(1)>', celular: true, site: 'javascript:alert(1)', avaliacoes: 10, nota_maps: 4.7,
    nota: 8, letra: 'A', motivos: ['<img src=y onerror=alert(2)> (+3)'], por_que_curto: ['<script>alert(3)</script>'],
    excluido_por: null, status: 'novo', anotacao: '', ...extra,
  };
}

test('el(): texto vira nó de texto, nunca elemento', () => {
  const caixa = el('div', {}, MALICIOSO, el('span', {}, '<b>x</b>'));
  assert.deepEqual(tags(caixa), ['DIV', 'SPAN']);
  assert.deepEqual(textos(caixa), [MALICIOSO, '<b>x</b>']);
});

test('el(): atributo de evento só aceita função', () => {
  assert.throws(() => el('div', { onclick: 'alert(1)' }), /Atributo de evento/);
  assert.throws(() => el('img', { onerror: 'alert(1)' }), /Atributo de evento/);
  const botao = el('button', { onClick: () => {} });
  assert.equal(botao.ouvintes.click.length, 1);
  assert.equal(botao.attributes.onclick, undefined);
});

test('el(): href e src nunca apontam para código', () => {
  for (const url of ['javascript:alert(1)', ' JavaScript:alert(1)', 'data:text/html,<script>', 'vbscript:x']) {
    assert.throws(() => el('a', { href: url }), /Endereço não permitido/, url);
    assert.throws(() => el('img', { src: url }), /Endereço não permitido/, url);
  }
  assert.equal(el('a', { href: 'https://ok.invalid/' }).attributes.href, 'https://ok.invalid/');
});

test('linha da tabela: nome malicioso aparece como texto, sem criar elemento nenhum', () => {
  const linha = leads.criarLinha(leadMalicioso(), () => {});
  const nomeCelula = linha.children[0];
  assert.equal(nomeCelula.children[0].tagName, 'B');          // o <b> é do painel, não do nome
  assert.equal(nomeCelula.children[0].textContent, MALICIOSO);  // o nome inteiro, como texto
  for (const tag of PERIGOSAS.filter((t) => t !== 'B')) assert.ok(!tags(linha).includes(tag), tag);
  assert.deepEqual(tags(linha).filter((t) => t === 'B'), ['B']);  // um só <b>: o do painel
});

test('linha da tabela: categoria, telefone e motivos também só viram texto', () => {
  const linha = leads.criarLinha(leadMalicioso(), () => {});
  const todos = textos(linha).join('|');
  assert.ok(todos.includes('<b>Padaria</b> · <svg onload=alert(1)>'));
  assert.ok(todos.includes('<script>alert(3)</script>'));
  for (const no of elementos(linha)) {
    assert.ok(!Object.keys(no.attributes).some((a) => a.toLowerCase().startsWith('on')), 'atributo de evento em ' + no.tagName);
    assert.equal(no.attributes.href, undefined);
    assert.equal(no.attributes.src, undefined);
  }
});

test('linha da tabela: o texto malicioso no title é só valor de atributo', () => {
  const linha = leads.criarLinha(leadMalicioso(), () => {});
  const porque = linha.children[5];
  assert.equal(porque.attributes.title, '<img src=y onerror=alert(2)> (+3)');
  assert.equal(porque.children.length, 1);
  assert.equal(porque.children[0].nodeType, 3);
});

test('linha da tabela: lead excluído mostra o motivo como texto e fica marcado', () => {
  const linha = leads.criarLinha(leadMalicioso({ excluido_por: 'sem telefone' }), () => {});
  assert.equal(linha.className, 'excluido');
  assert.ok(textos(linha).includes('Motivo: sem telefone'));
  assert.ok(textos(linha).includes('Fora da lista'));
});

test('linha da tabela: letra de qualidade desconhecida cai em C (classe nunca vem do dado)', () => {
  const linha = leads.criarLinha(leadMalicioso({ letra: 'A" onmouseover="alert(1)' }), () => {});
  const q = elementos(linha).find((n) => /\bq\b/.test(n.className));
  assert.equal(q.className, 'q C');
});

test('linha da tabela: clicar e Enter abrem o lead certo, Espaço também', () => {
  const abertos = [];
  const linha = leads.criarLinha(leadMalicioso({ id: 42 }), (id) => abertos.push(id));
  linha.ouvintes.click[0]();
  linha.ouvintes.keydown[0]({ key: 'Enter', preventDefault() {} });
  linha.ouvintes.keydown[0]({ key: ' ', preventDefault() {} });
  linha.ouvintes.keydown[0]({ key: 'a', preventDefault() {} });
  assert.deepEqual(abertos, [42, 42, 42]);
  assert.equal(linha.dataset.id, 42);
});

test('contato: site "javascript:" não vira link, aparece como texto', () => {
  const bloco = leads.blocoContato({ telefone: '(61) 99999-0001', site: 'javascript:alert(1)', link: 'data:text/html,x', emails: [], endereco: 'Rua A' });
  assert.ok(!tags(bloco).includes('A'));
  assert.ok(textos(bloco).includes('javascript:alert(1)'));
  assert.ok(!textos(bloco).includes('Ver no Google Maps'));
});

test('contato: site https vira link seguro, que abre em outra aba sem passar a referência', () => {
  const bloco = leads.blocoContato({ telefone: '', site: 'https://ok.invalid/menu?a=1', link: 'https://maps.invalid/x', emails: ['a@b.invalid'], endereco: 'Rua A' });
  const links = elementos(bloco).filter((n) => n.tagName === 'A');
  assert.equal(links.length, 2);
  for (const a of links) {
    assert.match(a.attributes.href, /^https:\/\//);
    assert.equal(a.attributes.target, '_blank');
    assert.equal(a.attributes.rel, 'noopener noreferrer');
  }
  assert.ok(textos(bloco).includes('a@b.invalid'));
});

test('contato: nome, e-mail e endereço com HTML ficam como texto', () => {
  const bloco = leads.blocoContato({ telefone: MALICIOSO, site: '', link: '', emails: [MALICIOSO], endereco: MALICIOSO });
  assert.ok(!tags(bloco).includes('IMG'));
  assert.equal(textos(bloco).filter((t) => t === MALICIOSO).length, 3);
});

test('por que: frases do servidor entram como texto, com os pontos', () => {
  const bloco = leads.blocoPorQue({ excluido_por: null, por_que: [{ texto: MALICIOSO, rotulo: 'x', pontos: 3 }, { texto: 'Ok.', rotulo: 'y', pontos: 1 }] });
  assert.ok(!tags(bloco).includes('IMG'));
  assert.ok(textos(bloco).includes(MALICIOSO));
  assert.ok(textos(bloco).includes('+3 pontos'));
  assert.ok(textos(bloco).includes('+1 ponto'));
});

test('por que: sem regra batida e lead excluído explicam em português simples', () => {
  assert.ok(textos(leads.blocoPorQue({ excluido_por: null, por_que: [] })).join(' ').includes('Nenhuma regra do seu perfil bateu'));
  const fora = leads.blocoPorQue({ excluido_por: 'possível rede (nome repetido em 3 endereços)', por_que: [] });
  assert.ok(textos(fora).join(' ').includes('Possível rede (nome repetido em 3 endereços).'));  // inicial maiúscula
  assert.ok(textos(fora).join(' ').includes('Só os excluídos'));
});

test('etiquetas de site e de telefone ignoram o conteúdo do dado', () => {
  assert.equal(leads.etiquetaDoSite('javascript:alert(1)').textContent, 'Tem site');
  assert.equal(leads.etiquetaDoSite('').textContent, 'Não tem');
  assert.equal(leads.etiquetaDoSite('https://www.instagram.com/x').textContent, 'Só rede social');
  assert.equal(leads.etiquetaDoTelefone({ telefone: '', celular: false }).textContent, 'Sem telefone');
  assert.equal(leads.etiquetaDoTelefone({ telefone: MALICIOSO, celular: true }).textContent, 'Celular');
  assert.equal(leads.etiquetaDoTelefone({ telefone: '3333', celular: false }).textContent, 'Fixo');
});

test('aviso de conformidade: mostra o que a pessoa informou, como texto', () => {
  const regulado = leads.blocoConformidade({ tipo: 'regulado', detalhe: MALICIOSO }, false);
  assert.ok(!tags(regulado).includes('IMG'));
  assert.ok(textos(regulado).join(' ').includes(MALICIOSO));
  assert.ok(textos(regulado).join(' ').includes('não é aconselhamento jurídico'));
  assert.ok(textos(regulado).join(' ').includes('Resposta: ' + MALICIOSO + '.'));
  assert.equal(regulado.attributes.role, 'note');
  assert.equal(leads.blocoConformidade(null, false), null);
  const incerto = leads.blocoConformidade({ tipo: 'incerto', detalhe: '' }, true);
  assert.ok(textos(incerto).join(' ').includes('não sabe'));
});

test('aviso de conformidade: texto exato, só fatos, sem prometer proteção', () => {
  const soTexto = (bloco) => textos(bloco.children[1]).join('');  // sem o "!" decorativo do selo
  const regulado = soTexto(leads.blocoConformidade({ tipo: 'regulado', detalhe: 'advocacia (OAB)' }, false));
  assert.equal(regulado,
    'Você informou que a sua área tem regras de publicidade ou de abordagem.'
    + ' Resposta: advocacia (OAB).'
    + ' Veja as regras do seu conselho ou órgão de classe antes de enviar qualquer mensagem.'
    + 'O kit não confere se uma mensagem cumpre essas regras. Os textos do kit são modelos, e enviar ou não é sempre decisão sua. Isto não é aconselhamento jurídico.');
  const incerto = soTexto(leads.blocoConformidade({ tipo: 'incerto', detalhe: '' }, false));
  assert.equal(incerto,
    'Você respondeu que não sabe se a sua área tem regras de publicidade ou de abordagem.'
    + ' Vale descobrir isso antes de enviar mensagens.'
    + 'O kit não confere se uma mensagem cumpre essas regras. Os textos do kit são modelos, e enviar ou não é sempre decisão sua. Isto não é aconselhamento jurídico.');
  const pequeno = soTexto(leads.blocoConformidade({ tipo: 'regulado', detalhe: '' }, true));
  assert.equal(pequeno, 'Você informou que a sua área tem regras de publicidade ou de abordagem. Veja as regras do seu conselho ou órgão de classe antes de enviar qualquer mensagem.');
  for (const texto of [regulado, incerto, pequeno]) {
    assert.doesNotMatch(texto, /protege|proteção|garant|isent|livre de|sem risco|cumpre a lei|em conformidade|seguro/i);
    assert.ok(!texto.includes('\u2014'));
  }
});
