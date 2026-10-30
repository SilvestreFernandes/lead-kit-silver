// Tela Minha oferta. O conteúdo chega na etapa 5 da fase 3.
import { cabecalhoDaTela, blocoEstado } from './dom.js';

export function montarOferta(raiz) {
  raiz.append(
    cabecalhoDaTela('Minha oferta', 'Conte o que você vende e como prefere falar. As mensagens usam isso.'),
    blocoEstado({ titulo: 'Esta tela ainda está sendo construída', texto: 'Ela chega na próxima etapa.' }));
}
