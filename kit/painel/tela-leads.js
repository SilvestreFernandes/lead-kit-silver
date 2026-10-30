// Tela Leads. O conteúdo chega na etapa 3 da fase 3.
import { cabecalhoDaTela, blocoEstado } from './dom.js';

export function montarLeads(raiz) {
  raiz.append(
    cabecalhoDaTela('Leads', 'Os negócios encontrados, já com nota e mensagem pronta.'),
    blocoEstado({ titulo: 'Esta tela ainda está sendo construída', texto: 'Ela chega na próxima etapa.' }));
}
