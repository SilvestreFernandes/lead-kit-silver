// DOM de mentira para os testes em Node. Ao contrário de uma string solta, ele sabe a diferença entre
// texto e elemento, então dá para provar que dado malicioso vira só texto. Importar este arquivo instala
// `document` e `Node` globais (por isso deve vir antes de importar os módulos do painel).
import assert from 'node:assert/strict';

export class FakeNode {}

export class FakeText extends FakeNode {
  constructor(dados) { super(); this.nodeType = 3; this.dados = String(dados); }
  get textContent() { return this.dados; }
}

export class FakeElement extends FakeNode {
  constructor(tag) {
    super();
    this.nodeType = 1;
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.ouvintes = {};
    this.className = '';
    this.hidden = false;
    this.style = {};
    this.classList = {
      toggle: (nome, ligado) => {
        const nomes = this.className.split(/\s+/).filter(Boolean).filter((n) => n !== nome);
        if (ligado) nomes.push(nome);
        this.className = nomes.join(' ');
      },
    };
  }
  setAttribute(nome, valor) {
    this.attributes[nome] = String(valor);
    if (nome === 'class') this.className = String(valor);
    if (nome === 'hidden') this.hidden = true;
  }
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
  set textContent(valor) { this.children = [new FakeText(valor)]; }
}

globalThis.Node = FakeNode;
globalThis.document = {
  createElement: (tag) => new FakeElement(tag),
  createTextNode: (texto) => new FakeText(texto),
  getElementById: () => null,
};

export function* percorrer(no) {
  yield no;
  for (const filho of no.children || []) yield* percorrer(filho);
}
export const elementos = (no) => [...percorrer(no)].filter((n) => n.nodeType === 1);
export const tags = (no) => elementos(no).map((n) => n.tagName);
export const textos = (no) => [...percorrer(no)].filter((n) => n.nodeType === 3).map((n) => n.dados);
export const textoTodo = (no) => textos(no).join(' ');
export const botoes = (no) => elementos(no).filter((n) => n.tagName === 'BUTTON');
