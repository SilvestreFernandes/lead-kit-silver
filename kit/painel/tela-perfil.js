// Tela mostrada quando não há perfil, ou quando o perfil tem problemas.
// O perfil é feito pela IA do usuário, numa entrevista curta. O painel só explica como e confere de novo.
import { el, blocoEstado, avisar, passoAPasso } from './dom.js';
import { PASSOS_PERFIL_AUSENTE } from './instrucoes.js';

function botaoVerificar(aoVerificar, aindaFalta, primario) {
  const botao = el('button', { class: 'btn' + (primario ? ' btn-primary' : ''), type: 'button' }, 'Verificar de novo');
  botao.addEventListener('click', async () => {
    botao.disabled = true;
    botao.textContent = 'Verificando...';
    try {
      await aoVerificar();
    } finally {
      // Se o perfil apareceu, esta tela já foi trocada e o botão saiu da página: nada a avisar.
      // Se o botão ainda está aqui, o problema continua.
      if (botao.isConnected) {
        botao.disabled = false;
        botao.textContent = 'Verificar de novo';
        avisar(aindaFalta);
      }
    }
  });
  return botao;
}

export function montarPerfilAusente(raiz, { aoVerificar }) {
  const passos = passoAPasso(PASSOS_PERFIL_AUSENTE);

  const bloco = blocoEstado({
    tipo: 'warn', selo: '!', nivel: 'h1',
    titulo: 'Falta o seu perfil',
    texto: 'O perfil é um resumo do que você vende e para quem. É com ele que o painel dá nota aos negócios e escreve as mensagens de abordagem. Quem monta o perfil é a sua IA, numa conversa curta de 12 perguntas.',
    extras: [
      passos,
      el('div', { class: 'acoes' }, botaoVerificar(aoVerificar, 'Ainda não achei o perfil. Termine a entrevista com a sua IA e tente de novo.', true)),
      el('details', {},
        el('summary', {}, 'Onde fica o perfil?'),
        el('p', {}, 'No arquivo dados/perfil.json, dentro da pasta do kit. Ele fica só no seu computador. Se você já tem um perfil pronto, coloque o arquivo nesse lugar e clique em Verificar de novo.')),
    ],
  });
  raiz.append(bloco);
}

export function montarPerfilInvalido(raiz, { erros, aoVerificar, irPara }) {
  const lista = erros && erros.length
    ? el('ul', { class: 'lista-erros' }, erros.map((e) => el('li', {}, e)))
    : null;
  const bloco = blocoEstado({
    tipo: 'warn', selo: '!', nivel: 'h1',
    titulo: 'Seu perfil precisa de ajustes',
    texto: 'O painel achou estes problemas no perfil. Enquanto eles existirem, não dá para buscar nem ver as notas dos leads.',
    extras: [
      lista,
      el('div', { class: 'acoes' },
        el('button', { class: 'btn btn-primary', type: 'button', onClick: () => irPara('oferta') }, 'Corrigir em Minha oferta'),
        botaoVerificar(aoVerificar, 'O perfil ainda tem problemas.', false)),
      el('p', {}, 'Se preferir, peça para a sua IA refazer a entrevista. O perfil antigo fica guardado como perfil.anterior.json.'),
    ],
  });
  raiz.append(bloco);
}
