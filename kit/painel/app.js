// Casca do painel: cabeçalho, abas, estado do motor e do perfil, avisos e troca de tela.
// Cada tela fica em seu próprio arquivo e só recebe a área onde deve se desenhar.
import { ler, seguidor, ABANDONADA, ErroApi } from './api.js';
import {
  ABAS, INTERVALO_ESTADO_MS, abaDoHash, hashDaAba, abaVizinha, situacaoDoPerfil, abasHabilitadas,
  temaAlternado, textoDaFalha, COMANDO_LIGAR_KIT, COMANDO_LIGAR_MOTOR,
} from './util.js';
import { el, limpar, blocoEstado, blocoCarregando, comando, avisar } from './dom.js';
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
  chaveTela: null,     // para não redesenhar a tela (e apagar o que a pessoa digitou) a cada verificação
  limparTela: null,    // função da tela atual para desfazer o que ela montou
};

const seguirEstado = seguidor();

export async function atualizarEstado() {
  const resultado = await seguirEstado((sinal) => ler('/api/estado', null, sinal).then(
    (estado) => ({ estado }),
    (erro) => { if (erro instanceof ErroApi) return { erro }; throw erro; }));
  if (resultado === ABANDONADA) return app.estado;
  if (resultado.estado) { app.estado = resultado.estado; app.falha = null; } else { app.falha = resultado.erro; }
  app.carregou = true;
  desenhar();
  return app.estado;
}

function irPara(aba) {
  if (location.hash === hashDaAba(aba)) { app.aba = aba; desenhar(); } else { location.hash = hashDaAba(aba); }
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
  limpar(area.avisos);
  if (!app.carregou) return;
  if (app.falha && app.falha.tipo === 'rede' && app.estado) {
    area.avisos.append(faixa('bad',
      el('p', {}, el('b', {}, 'O kit parou de responder. '), 'Ligue de novo com o comando ao lado e clique em Tentar de novo.'),
      el('div', { class: 'acoes' }, comando(COMANDO_LIGAR_KIT), botaoPequeno('Tentar de novo', () => atualizarEstado(), true))));
  } else if (app.falha && app.falha.tipo === 'token') {
    area.avisos.append(faixa('warn',
      el('p', {}, el('b', {}, 'A página ficou desatualizada. '), 'O kit foi reiniciado depois que você abriu esta página. Recarregue para continuar.'),
      el('div', { class: 'acoes' }, botaoPequeno('Recarregar a página', () => location.reload(), true))));
  } else if (app.estado && !app.estado.motor_no_ar) {
    area.avisos.append(faixa('warn',
      el('p', {}, el('b', {}, 'O motor de busca está desligado. '),
        'Você ainda vê os leads salvos, mas não dá para fazer buscas novas. Ligue com o comando ao lado e espere uns 20 segundos.'),
      el('div', { class: 'acoes' }, comando(COMANDO_LIGAR_MOTOR), botaoPequeno('Verificar de novo', () => atualizarEstado(), true))));
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
    estado: () => app.estado, avisar, irPara, atualizarEstado,
  };
  const aoVerificar = () => atualizarEstado();

  if (escolha.chave === 'carregando') {
    area.tela.append(blocoCarregando('Carregando o painel...'));
  } else if (!app.estado) {
    const { titulo, texto } = textoDaFalha(app.falha ? app.falha.tipo : 'rede', app.falha && app.falha.message);
    area.tela.append(blocoEstado({
      tipo: 'bad', selo: '!', nivel: 'h1', titulo, texto,
      extras: app.falha && app.falha.tipo === 'rede' ? [comando(COMANDO_LIGAR_KIT)] : [],
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
