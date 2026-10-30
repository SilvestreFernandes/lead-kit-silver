// Fala com o servidor local. Só chama a própria origem (127.0.0.1), nunca outro endereço.
// Escritas levam o token da página (X-Token). Falhas viram ErroApi, com mensagem em português.
import { montarQuery, classificarFalha, textoDaFalha } from './util.js';

export class ErroApi extends Error {
  constructor(tipo, mensagem, { status = 0, erros = [], extra = {} } = {}) {
    super(mensagem);
    this.name = 'ErroApi';
    this.tipo = tipo;        // rede | token | recusado | naoencontrado | conflito | ocupado | servidor | pedido
    this.status = status;
    this.erros = erros;      // lista de problemas (ex.: erros de validação do perfil)
    this.extra = extra;      // corpo inteiro da resposta de erro
  }
}

function tokenDaPagina() {
  const meta = document.querySelector('meta[name="token"]');
  return meta ? meta.content : '';
}

async function pedir(metodo, caminho, { params, corpo, sinal } = {}) {
  const cabecalhos = { Accept: 'application/json' };
  const opcoes = { method: metodo, headers: cabecalhos, signal: sinal, credentials: 'same-origin', cache: 'no-store' };
  if (metodo !== 'GET') {
    cabecalhos['X-Token'] = tokenDaPagina();
    cabecalhos['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(corpo === undefined ? {} : corpo);
  }
  let resposta;
  try {
    resposta = await fetch(caminho + montarQuery(params), opcoes);
  } catch (erro) {
    if (erro && erro.name === 'AbortError') throw erro;
    throw new ErroApi('rede', textoDaFalha('rede').titulo);
  }
  const texto = await resposta.text();
  let dados = null;
  try { dados = JSON.parse(texto); } catch (erro) { /* resposta sem JSON */ }
  if (!resposta.ok) {
    const tipo = classificarFalha(resposta.status);
    const mensagem = (dados && dados.erro) || textoDaFalha(tipo).texto;
    throw new ErroApi(tipo, mensagem, {
      status: resposta.status, erros: (dados && dados.erros) || [], extra: dados || {},
    });
  }
  return dados;
}

export function ler(caminho, params, sinal) {
  return pedir('GET', caminho, { params, sinal });
}

export function escrever(metodo, caminho, corpo, sinal) {
  return pedir(metodo, caminho, { corpo, sinal });
}

// Endereço para baixar um arquivo (exportação). Leitura não precisa de token.
export function urlDownload(caminho, params) {
  return caminho + montarQuery(params);
}

// Marca de "resposta descartada": chegou depois de um pedido mais novo ter saído.
export const ABANDONADA = Symbol('abandonada');

// Só a última chamada vale. Chamar de novo cancela a anterior, e uma resposta velha nunca
// sobrescreve uma nova (ex.: digitar na busca por texto).
export function seguidor() {
  let atual = null;
  return async function (fazer) {
    if (atual) atual.abort();
    const controle = new AbortController();
    atual = controle;
    try {
      const resultado = await fazer(controle.signal);
      return atual === controle ? resultado : ABANDONADA;
    } catch (erro) {
      if (erro && erro.name === 'AbortError') return ABANDONADA;
      throw erro;
    } finally {
      if (atual === controle) atual = null;
    }
  };
}
