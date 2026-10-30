// Fala com o servidor local. Só chama a própria origem (127.0.0.1), nunca outro endereço.
// Escritas e downloads levam o token da página (X-Token). Falhas viram ErroApi, com mensagem em português.
import { montarQuery, classificarFalha, textoDaFalha, nomeDoArquivo } from './util.js';

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

async function enviar(metodo, caminho, { params, corpo, sinal, comToken } = {}) {
  const cabecalhos = {};
  if (!comToken) cabecalhos.Accept = 'application/json';  // download de arquivo usa o padrão do navegador
  const opcoes = { method: metodo, headers: cabecalhos, signal: sinal, credentials: 'same-origin', cache: 'no-store' };
  if (metodo !== 'GET' || comToken) cabecalhos['X-Token'] = tokenDaPagina();
  if (metodo !== 'GET') {
    cabecalhos['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(corpo === undefined ? {} : corpo);
  }
  try {
    return await fetch(caminho + montarQuery(params), opcoes);
  } catch (erro) {
    if (erro && erro.name === 'AbortError') throw erro;
    throw new ErroApi('rede', textoDaFalha('rede').titulo + '. Confira se ele está ligado.');
  }
}

async function erroDaResposta(resposta) {
  const texto = await resposta.text();
  let dados = null;
  try { dados = JSON.parse(texto); } catch (erro) { /* resposta sem JSON */ }
  const tipo = classificarFalha(resposta.status);
  return new ErroApi(tipo, (dados && dados.erro) || textoDaFalha(tipo).texto, {
    status: resposta.status, erros: (dados && dados.erros) || [], extra: dados || {},
  });
}

async function pedir(metodo, caminho, opcoes) {
  const resposta = await enviar(metodo, caminho, opcoes);
  if (!resposta.ok) throw await erroDaResposta(resposta);
  const texto = await resposta.text();
  try { return JSON.parse(texto); } catch (erro) { return null; }
}

export function ler(caminho, params, sinal) {
  return pedir('GET', caminho, { params, sinal });
}

export function escrever(metodo, caminho, corpo, sinal) {
  return pedir(metodo, caminho, { corpo, sinal });
}

async function pedirArquivo(caminho, params, sinal) {
  const resposta = await enviar('GET', caminho, { params, sinal, comToken: true });
  if (!resposta.ok) throw await erroDaResposta(resposta);
  return { blob: await resposta.blob(), nome: nomeDoArquivo(resposta.headers.get('Content-Disposition')) };
}

// Baixa um arquivo (exportação). Leva o token, como as escritas, porque entrega os dados dos leads.
// Devolve { blob, nome }.
export function baixar(caminho, params, sinal) {
  return pedirArquivo(caminho, params, sinal);
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
