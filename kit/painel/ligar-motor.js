// Botão "Ligar o motor": pede ao kit para ligar o motor de busca e acompanha pelo estado do kit.
// O comando roda no servidor, fixo, sem nada digitado aqui. O painel só mostra a mensagem simples.
// Só aparece quando o Docker está ligado e falta ligar o motor. Nos outros casos, vale o passo a passo manual.
import { el } from './dom.js';
import { escrever, ErroApi } from './api.js';

export const INTERVALO_LIGANDO_MS = 3000;
export const TEXTO_LIGANDO = 'Ligando o motor. Pode levar alguns minutos, principalmente na primeira vez, porque o Docker pode precisar baixar o motor. Pode deixar esta página aberta.';

export function podeLigarPeloPainel(estado) {
  const d = estado && estado.motor_diagnostico;
  return !!(estado && estado.motor_no_ar === false && d && d.estado === 'motor_parado');
}

export function estaLigando(estado) {
  return !!(estado && estado.ligando_motor && estado.ligando_motor.estado === 'ligando');
}

// Muda só quando algo que a tela mostra mudou. Serve para não redesenhar (e fechar o "passo a passo") a cada verificação.
export function chaveDoMotor(estado) {
  if (!estado) return '';
  const d = estado.motor_diagnostico;
  const l = estado.ligando_motor;
  return JSON.stringify([estado.motor_no_ar, d ? d.estado : null, l ? [l.estado, l.mensagem] : null]);
}

let acompanhando = false;
const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

// Verifica o estado de 3 em 3 segundos enquanto o comando roda (o ciclo normal é de 10 s).
export async function acompanharLigacao(atualizarEstado) {
  if (acompanhando) return;
  acompanhando = true;
  try {
    for (let i = 0; i < 200; i += 1) {
      const estado = await atualizarEstado();
      if (!estaLigando(estado) || (estado && estado.motor_no_ar)) return;
      await esperar(INTERVALO_LIGANDO_MS);
    }
  } finally {
    acompanhando = false;
  }
}

// Devolve o bloco do botão (ou null quando o botão não ajudaria).
export function criarLigarMotor({ estado, atualizarEstado, avisar }) {
  if (!podeLigarPeloPainel(estado)) return null;
  const situacao = estado.ligando_motor;
  const ligando = estaLigando(estado);
  const botao = el('button', { class: 'btn btn-primary', type: 'button', disabled: ligando || null }, 'Ligar o motor');
  botao.addEventListener('click', async () => {
    botao.disabled = true;
    try {
      await escrever('POST', '/api/motor/ligar');
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (avisar) avisar(erro.message);
    }
    await acompanharLigacao(atualizarEstado);
  });
  return el('div', { class: 'ligar-motor' },
    ligando ? el('p', { class: 'ligando', role: 'status' }, situacao.mensagem || TEXTO_LIGANDO) : null,
    !ligando && situacao ? el('p', { class: situacao.estado === 'erro' ? 'erro-simples' : 'nota' }, situacao.mensagem) : null,
    el('div', { class: 'acoes' }, botao));
}
