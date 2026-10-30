// Construção de elementos da página SEM innerHTML. Todo texto entra como texto (textContent),
// porque nome, endereço e telefone vêm do Google Maps e não são confiáveis.

export function el(tag, atributos, ...filhos) {
  const no = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos || {})) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (chave === 'class') no.className = valor;
    else if (chave === 'dataset') Object.assign(no.dataset, valor);
    else if (chave.startsWith('on') && typeof valor === 'function') no.addEventListener(chave.slice(2).toLowerCase(), valor);
    else no.setAttribute(chave, valor === true ? '' : String(valor));
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

// Comando para copiar e colar no terminal, com botão de copiar.
export function comando(texto) {
  return el('div', { class: 'cmd' },
    el('code', {}, texto),
    el('button', {
      class: 'btn btn-small', type: 'button',
      onClick: async () => avisar((await copiarTexto(texto)) ? 'Comando copiado.' : 'Não consegui copiar. Selecione o texto e use Ctrl+C.'),
    }, 'Copiar'));
}
