// Construção de elementos da página SEM innerHTML. Todo texto entra como texto (textContent),
// porque nome, endereço e telefone vêm do Google Maps e não são confiáveis.

// Atributos que carregam endereço: nunca podem apontar para código.
const ATRIBUTOS_DE_ENDERECO = ['href', 'src', 'action', 'formaction', 'xlink:href'];
const ESQUEMA_PERIGOSO = /^\s*(javascript|data|vbscript):/i;

export function el(tag, atributos, ...filhos) {
  const no = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos || {})) {
    if (valor === null || valor === undefined || valor === false) continue;
    const nome = chave.toLowerCase();
    if (nome.startsWith('on')) {
      // Só função vira ouvinte de evento. Texto num atributo de evento seria código escrito na página.
      if (typeof valor !== 'function') throw new Error('Atributo de evento só aceita função: ' + chave);
      no.addEventListener(nome.slice(2), valor);
    } else if (chave === 'class') no.className = valor;
    else if (chave === 'dataset') Object.assign(no.dataset, valor);
    else {
      if (ATRIBUTOS_DE_ENDERECO.includes(nome) && ESQUEMA_PERIGOSO.test(String(valor))) {
        throw new Error('Endereço não permitido em ' + chave);
      }
      no.setAttribute(chave, valor === true ? '' : String(valor));
    }
  }
  anexar(no, filhos);
  return no;
}

function anexar(no, filhos) {
  for (const filho of filhos) {
    if (filho === null || filho === undefined || filho === false) continue;
    if (Array.isArray(filho)) anexar(no, filho);
    else no.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
}

export function limpar(no) {
  while (no.firstChild) no.removeChild(no.firstChild);
  return no;
}

export function cabecalhoDaTela(titulo, texto) {
  return el('div', { class: 'page-head' }, el('h1', {}, titulo), texto ? el('p', {}, texto) : null);
}

// acoes: [{ rotulo, aoClicar, primario }]
export function botoes(acoes) {
  return el('div', { class: 'acoes' }, (acoes || []).map((a) =>
    el('button', { class: 'btn' + (a.primario ? ' btn-primary' : ''), type: 'button', onClick: a.aoClicar }, a.rotulo)));
}

// Cartão de estado: carregando, vazio, erro, perfil ausente. tipo: neutro | warn | bad | good.
export function blocoEstado({ tipo = 'neutro', selo = 'i', titulo, texto, extras = [], acoes = [], nivel = 'h2' }) {
  return el('section', { class: 'card estado', dataset: { tipo } },
    el('div', { class: 'selo', 'aria-hidden': 'true' }, selo),
    el(nivel, {}, titulo),
    texto ? el('p', {}, texto) : null,
    extras,
    acoes.length ? botoes(acoes) : null);
}

export function blocoCarregando(texto) {
  return el('section', { class: 'card estado', role: 'status' },
    el('div', { class: 'carregando' }, el('span', { class: 'giro', 'aria-hidden': 'true' }), el('span', {}, texto)));
}

export async function copiarTexto(texto) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch (erro) { /* cai no plano B */ }
  try {
    const area = el('textarea', { 'aria-hidden': 'true', style: 'position:fixed;left:-9999px;top:0' });
    area.value = texto;
    document.body.append(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    return ok;
  } catch (erro) {
    return false;
  }
}

let temporizadorAviso = null;
export function avisar(texto) {
  const caixa = document.getElementById('toast');
  if (!caixa) return;
  caixa.textContent = texto;
  caixa.hidden = false;
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => { caixa.hidden = true; }, 3200);
}

// Lista numerada de passos, em palavras simples.
export function passoAPasso(passos) {
  return el('ol', { class: 'passos' }, passos.map((p) => el('li', {}, el('span', {}, p))));
}

// Passo a passo (onde e como) seguido do comando com botão de copiar.
// É a única forma de mostrar um comando na tela: a pessoa nunca recebe um comando sem saber onde digitar.
// Com `recolhido`, os passos ficam numa seção que se abre ao clicar (para faixas de aviso).
export function instrucoesComComando({ passos, comando: texto, recolhido }) {
  const lista = passoAPasso(passos);
  const caixa = texto ? comando(texto) : null;
  if (recolhido) {
    return [el('details', { class: 'como-fazer' }, el('summary', {}, 'Como fazer, passo a passo'), lista, caixa)];
  }
  return [lista, caixa];
}

// Comando para copiar e colar no terminal, com botão de copiar.
// Use instrucoesComComando: ele acompanha o passo a passo de onde digitar.
export function comando(texto) {
  return el('div', { class: 'cmd' },
    el('code', {}, texto),
    el('button', {
      class: 'btn btn-small', type: 'button',
      onClick: async () => avisar((await copiarTexto(texto)) ? 'Comando copiado.' : 'Não consegui copiar. Selecione o texto e use Ctrl+C.'),
    }, 'Copiar'));
}
