// Tela Buscar. O conteúdo chega na etapa 4 da fase 3.
import { cabecalhoDaTela, blocoEstado } from './dom.js';

export function montarBuscar(raiz) {
  raiz.append(
    cabecalhoDaTela('Buscar leads', 'Escolha o tipo de negócio e a cidade. O painel busca no Google Maps e já dá nota a cada lead.'),
    blocoEstado({ titulo: 'Esta tela ainda está sendo construída', texto: 'Ela chega na próxima etapa.' }));
}
