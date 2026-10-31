// Casca do painel: cabeçalho, abas, estado do motor e do perfil, avisos e troca de tela.
// Cada tela fica em seu próprio arquivo e só recebe a área onde deve se desenhar.
import { ler, seguidor, ABANDONADA, ErroApi } from './api.js';
import {
  ABAS, INTERVALO_ESTADO_MS, abaDoHash, hashDaAba, abaVizinha, situacaoDoPerfil, abasHabilitadas,
  temaAlternado, textoDaFalha,
} from './util.js';
import { el, limpar, blocoEstado, blocoCarregando, instrucoesComComando, avisar } from './dom.js';
import { COMANDO_LIGAR_KIT, PASSOS_LIGAR_KIT, motivoDoMotor } from './instrucoes.js';
import { criarLigarMotor, podeLigarPeloPainel, chaveDoMotor } from './ligar-motor.js';
import { montarPerfilAusente, montarPerfilInvalido } from './tela-perfil.js';
import { montarBuscar } from './tela-buscar.js';
import { montarLeads } from './tela-leads.js';
import { montarOferta } from './tela-oferta.js';

const TELAS = { buscar: montarBuscar, leads: montarLeads, oferta: montarOferta };

const $ = (seletor) => document.querySelector(seletor);
const area = { tela: $('#tela'), avisos: $('#avisos'), motor: $('#motor'), motorTexto: $('#motor-texto') };

const app = {
  estado: null,        // última resposta de /api/estado
  falha: null,         // ErroApi da última tentativa, ou null
  carregou: false,     // já tentou ao menos uma vez
  aba: abaDoHash(location.hash),
  chaveAvisos: null,   // o que as faixas de aviso mostram agora, para não redesenhar à toa
  chaveTela: null,     // para não redesenhar a tela (e apagar o que a pessoa digitou) a cada verificação
  limparTela: null,    // função da tela atual para desfazer o que ela montou
  parametros: null,    // recado de uma tela para a próxima (ex.: abrir Leads filtrado por uma busca)
  ouvintes: new Set(), // telas que querem saber quando o estado do kit muda
};

const seguirEstado = seguidor();

// Número ao lado de "Leads". null ou indefinido não muda nada.
function atualizarContagem(n) {
  if (n === null || n === undefined) return;
  const marca = $('#aba-leads-contagem');
  marca.textContent = String(n);
  marca.hidden = n === 0;
}

async function carregarContagemDeLeads() {
  if (app.contagemCarregada) return;
  app.contagemCarregada = true;
  try {
    const dados = await ler('/api/leads', { limite: 1 });
    atualizarContagem(dados.total);
  } catch (erro) {
    if (!(erro instanceof ErroApi)) throw erro;
    app.contagemCarregada = false;  // tenta de novo na próxima verificação
  }
}

export async function atualizarEstado() {
  const resultado = await seguirEstado((sinal) => ler('/api/estado', null, sinal).then(
    (estado) => ({ estado }),
    (erro) => { if (erro instanceof ErroApi) return { erro }; throw erro; }));
  if (resultado === ABANDONADA) return app.estado;
  if (resultado.estado) { app.estado = resultado.estado; app.falha = null; } else { app.falha = resultado.erro; }
  app.carregou = true;
  desenhar();
  if (situacaoDoPerfil(app.estado) === 'ok') carregarContagemDeLeads();
  return app.estado;
}

function irPara(aba, parametros) {
  app.parametros = parametros || null;
  if (location.hash === hashDaAba(aba)) { app.aba = aba; desenhar(); } else { location.hash = hashDaAba(aba); }
}

// A tela que abre pega o recado (uma vez só).
function consumirParametros() {
  const recado = app.parametros;
  app.parametros = null;
  return recado;
}

// Depois de uma busca terminar, o número ao lado de "Leads" precisa ser lido de novo.
function recarregarContagem() {
  app.contagemCarregada = false;
  return carregarContagemDeLeads();
}

function observarEstado(funcao) {
  app.ouvintes.add(funcao);
  return () => app.ouvintes.delete(funcao);
}

// ---------- cabeçalho, abas e avisos

function desenharMotor() {
  let estado = 'verificando';
  let texto = 'Verificando o motor';
  if (app.carregou) {
    if (app.falha && app.falha.tipo === 'rede') { estado = 'parado'; texto = 'Kit parado'; }
    else if (app.estado && app.estado.motor_no_ar) { estado = 'ligado'; texto = 'Motor local ligado'; }
    else if (app.estado) { estado = 'desligado'; texto = 'Motor desligado'; }
    else { estado = 'parado'; texto = 'Sem resposta do kit'; }
  }
  area.motor.dataset.estado = estado;
  area.motorTexto.textContent = texto;
}

function desenharAbas() {
  const situacao = situacaoDoPerfil(app.estado);
  const habilitadas = abasHabilitadas(situacao);
  const selecionada = habilitadas.includes(app.aba) ? app.aba : null;
  const foco = selecionada || habilitadas[0] || ABAS[0];
  for (const aba of ABAS) {
    const botao = $('#aba-' + aba);
    botao.setAttribute('aria-selected', aba === selecionada ? 'true' : 'false');
    botao.setAttribute('aria-disabled', habilitadas.includes(aba) ? 'false' : 'true');
    botao.tabIndex = aba === foco ? 0 : -1;
  }
}

function faixa(tipo, ...filhos) {
  return el('div', { class: 'aviso ' + tipo, role: 'alert' }, el('div', { class: 'wrap' }, filhos));
}

function botaoPequeno(rotulo, aoClicar, primario) {
  return el('button', { class: 'btn btn-small' + (primario ? ' btn-primary' : ''), type: 'button', onClick: aoClicar }, rotulo);
}

function desenharAvisos() {
  // Só redesenha quando algo mudou: assim o "passo a passo" aberto não fecha a cada verificação.
  const chave = JSON.stringify([app.carregou, app.falha && app.falha.tipo, !!app.estado,
    chaveDoMotor(app.estado), app.aba === 'buscar', app.estado ? situacaoDoPerfil(app.estado) : null]);
  if (chave === app.chaveAvisos) return;
  app.chaveAvisos = chave;
  limpar(area.avisos);
  if (!app.carregou) return;
  if (app.falha && app.falha.tipo === 'rede' && app.estado) {
    area.avisos.append(faixa('bad',
      el('p', {}, el('b', {}, 'O kit parou de responder. '), 'Ele pode ter sido fechado. Abra "Como fazer" para ligar de novo e clique em Tentar de novo.'),
      ...instrucoesComComando({ passos: PASSOS_LIGAR_KIT, comando: COMANDO_LIGAR_KIT, recolhido: true }),
      el('div', { class: 'acoes' }, botaoPequeno('Tentar de novo', () => atualizarEstado(), true))));
  } else if (app.falha && app.falha.tipo === 'token') {
    area.avisos.append(faixa('warn',
      el('p', {}, el('b', {}, 'A página ficou desatualizada. '), 'O kit foi reiniciado depois que você abriu esta página. Recarregue para continuar.'),
      el('div', { class: 'acoes' }, botaoPequeno('Recarregar a página', () => location.reload(), true))));
  } else if (app.estado && !app.estado.motor_no_ar && !(app.aba === 'buscar' && situacaoDoPerfil(app.estado) === 'ok')) {
    // Na aba Buscar a própria tela mostra o motivo com mais detalhe; nas outras, a faixa avisa.
    const motivo = motivoDoMotor(app.estado.motor_diagnostico);
    area.avisos.append(faixa('warn',
      el('p', {}, el('b', {}, motivo.titulo + '. '), 'Você ainda vê os leads salvos, mas não dá para fazer buscas novas. ' + motivo.texto),
      criarLigarMotor({ estado: app.estado, atualizarEstado, avisar }),
      ...instrucoesComComando({ passos: motivo.passos, comando: motivo.comando, recolhido: true,
        titulo: podeLigarPeloPainel(app.estado) ? 'Prefere ligar sozinho? Veja o passo a passo' : undefined }),
      el('div', { class: 'acoes' }, botaoPequeno('Verificar de novo', () => atualizarEstado(), true))));
  }
}

// ---------- tela principal

function escolherTela() {
  if (!app.carregou) return { chave: 'carregando' };
  if (!app.estado) return { chave: 'falha-inicial:' + (app.falha ? app.falha.tipo : '') };
  const situacao = situacaoDoPerfil(app.estado);
  if (situacao === 'ausente') return { chave: 'perfil-ausente', situacao };
  if (situacao === 'invalido' && app.aba !== 'oferta') {
    return { chave: 'perfil-invalido:' + JSON.stringify(app.estado.perfil.erros), situacao };
  }
  return { chave: 'aba:' + app.aba + ':' + situacao, situacao };
}

function desenharTela() {
  const escolha = escolherTela();
  if (escolha.chave === app.chaveTela) return;
  app.chaveTela = escolha.chave;
  if (app.limparTela) { app.limparTela(); app.limparTela = null; }
  limpar(area.tela);
  area.tela.removeAttribute('aria-labelledby');

  const contexto = {
    estado: () => app.estado, avisar, irPara, atualizarEstado, atualizarContagem,
    consumirParametros, recarregarContagem, observarEstado,
  };
  const aoVerificar = () => atualizarEstado();

  if (escolha.chave === 'carregando') {
    area.tela.append(blocoCarregando('Carregando o painel...'));
  } else if (!app.estado) {
    const { titulo, texto } = textoDaFalha(app.falha ? app.falha.tipo : 'rede', app.falha && app.falha.message);
    area.tela.append(blocoEstado({
      tipo: 'bad', selo: '!', nivel: 'h1', titulo, texto,
      extras: app.falha && app.falha.tipo === 'rede'
        ? instrucoesComComando({ passos: PASSOS_LIGAR_KIT, comando: COMANDO_LIGAR_KIT }) : [],
      acoes: [{ rotulo: 'Tentar de novo', primario: true, aoClicar: () => atualizarEstado() }],
    }));
  } else if (escolha.chave === 'perfil-ausente') {
    montarPerfilAusente(area.tela, { aoVerificar });
  } else if (escolha.chave.startsWith('perfil-invalido')) {
    montarPerfilInvalido(area.tela, { erros: app.estado.perfil.erros, aoVerificar, irPara });
  } else {
    const limpeza = TELAS[app.aba](area.tela, contexto);
    app.limparTela = typeof limpeza === 'function' ? limpeza : null;
  }
}

function desenhar() {
  desenharMotor();
  desenharAbas();
  desenharAvisos();
  desenharTela();
  for (const ouvinte of [...app.ouvintes]) ouvinte();
}

// ---------- ligações com a página

function ligarAbas() {
  const lista = $('#abas');
  lista.addEventListener('click', (evento) => {
    const botao = evento.target.closest('[data-aba]');
    if (!botao) return;
    const aba = botao.dataset.aba;
    if (!abasHabilitadas(situacaoDoPerfil(app.estado)).includes(aba)) {
      avisar(app.estado ? 'Primeiro falta o perfil. Veja o que fazer na tela.' : 'O painel ainda está carregando.');
      return;
    }
    irPara(aba);
  });
  lista.addEventListener('keydown', (evento) => {
    const habilitadas = abasHabilitadas(situacaoDoPerfil(app.estado));
    if (!habilitadas.length) return;
    const nova = abaVizinha(app.aba, evento.key, habilitadas);
    if (!nova) return;
    evento.preventDefault();
    irPara(nova);
    $('#aba-' + nova).focus();
  });
  window.addEventListener('hashchange', () => { app.aba = abaDoHash(location.hash); desenhar(); });
}

function ligarTema() {
  $('#tema').addEventListener('click', () => {
    const raiz = document.documentElement;
    const novo = temaAlternado(raiz.getAttribute('data-theme'), matchMedia('(prefers-color-scheme: dark)').matches);
    raiz.setAttribute('data-theme', novo);
    try { localStorage.setItem('lks-tema', novo); } catch (erro) { /* sem armazenamento: vale só nesta visita */ }
  });
}

function iniciar() {
  ligarAbas();
  ligarTema();
  desenhar();
  atualizarEstado();
  setInterval(() => { if (!document.hidden) atualizarEstado(); }, INTERVALO_ESTADO_MS);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) atualizarEstado(); });
}

iniciar();
