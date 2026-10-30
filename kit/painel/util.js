// Funções puras do painel: não mexem na página nem na rede, por isso são fáceis de testar.

export const ABAS = ['buscar', 'leads', 'oferta'];
export const INTERVALO_ESTADO_MS = 10000;

// { a: 1, b: '', c: [1, 2] } -> '?a=1&c=1%2C2'. Ignora vazio, nulo e falso.
export function montarQuery(params) {
  const partes = [];
  for (const [chave, valor] of Object.entries(params || {})) {
    if (valor === null || valor === undefined || valor === false) continue;
    const texto = Array.isArray(valor) ? valor.join(',') : String(valor);
    if (texto === '') continue;
    partes.push(encodeURIComponent(chave) + '=' + encodeURIComponent(texto));
  }
  return partes.length ? '?' + partes.join('&') : '';
}

export function plural(n, um, varios) {
  return n === 1 ? um : varios;
}

export function abaDoHash(hash) {
  const achou = /^#\/([a-z]+)$/.exec(hash || '');
  return achou && ABAS.includes(achou[1]) ? achou[1] : 'buscar';
}

export function hashDaAba(aba) {
  return '#/' + aba;
}

// Teclado nas abas: setas, Home e End. Devolve a aba nova, ou null se a tecla não é de navegação.
export function abaVizinha(atual, tecla, abas) {
  const lista = abas && abas.length ? abas : ABAS;
  const i = Math.max(0, lista.indexOf(atual));
  if (tecla === 'ArrowRight') return lista[(i + 1) % lista.length];
  if (tecla === 'ArrowLeft') return lista[(i - 1 + lista.length) % lista.length];
  if (tecla === 'Home') return lista[0];
  if (tecla === 'End') return lista[lista.length - 1];
  return null;
}

// 'desconhecida' (ainda não sabemos), 'ausente' (não há arquivo), 'invalido' ou 'ok'.
export function situacaoDoPerfil(estado) {
  if (!estado || !estado.perfil) return 'desconhecida';
  if (!estado.perfil.existe) return 'ausente';
  if (!estado.perfil.valido) return 'invalido';
  return 'ok';
}

// Quais abas funcionam em cada situação do perfil. Sem perfil válido só dá para corrigir em Minha oferta.
export function abasHabilitadas(situacao) {
  if (situacao === 'ok') return ABAS.slice();
  if (situacao === 'invalido') return ['oferta'];
  return [];
}

// Alterna entre claro e escuro. `atual` é o que está gravado na página (null = segue o sistema).
export function temaAlternado(atual, sistemaEscuro) {
  const efetivo = atual || (sistemaEscuro ? 'dark' : 'light');
  return efetivo === 'dark' ? 'light' : 'dark';
}

// Tipo da falha a partir do status HTTP (0 = nem chegou no servidor).
export function classificarFalha(status) {
  if (!status) return 'rede';
  if (status === 401) return 'token';
  if (status === 403) return 'recusado';
  if (status === 404) return 'naoencontrado';
  if (status === 409) return 'conflito';
  if (status === 503) return 'ocupado';
  if (status >= 500) return 'servidor';
  return 'pedido';
}

export function textoDaFalha(tipo, mensagemDoServidor) {
  switch (tipo) {
    case 'rede':
      return { titulo: 'O kit parou de responder',
        texto: 'Ele pode ter sido fechado. Ligue de novo com o comando abaixo e clique em Tentar de novo.' };
    case 'token':
      return { titulo: 'A página ficou desatualizada',
        texto: 'O kit foi reiniciado depois que você abriu esta página. Recarregue a página para continuar.' };
    case 'servidor':
      return { titulo: 'Algo deu errado dentro do kit',
        texto: 'Veja a janela onde o kit está rodando. Se o problema continuar, feche e abra o kit de novo.' };
    case 'recusado':
      return { titulo: 'Pedido recusado', texto: mensagemDoServidor || 'O kit recusou este pedido.' };
    default:
      return { titulo: 'Não deu certo', texto: mensagemDoServidor || 'Tente de novo em instantes.' };
  }
}

export const COMANDO_LIGAR_KIT = 'python kit/servidor.py';
export const COMANDO_LIGAR_MOTOR = 'docker compose up -d';

// ---------- Leads

export const PAGINA_LEADS = 100;
export const STATUS_DO_LEAD = ['novo', 'contatado', 'respondeu', 'fechado', 'descartado'];
const ROTULOS_DE_STATUS = {
  novo: 'Novo', contatado: 'Contatado', respondeu: 'Respondeu', fechado: 'Fechado', descartado: 'Descartado',
};

export function rotuloDoStatus(status) {
  return ROTULOS_DE_STATUS[status] || 'Novo';
}

// '4.8' -> '4,8'. Sem nota, um traço.
export function formatarNota(nota) {
  if (nota === null || nota === undefined || Number.isNaN(Number(nota))) return '-';
  return String(Number(nota)).replace('.', ',');
}

// 'nenhum' (sem site), 'rede' (o "site" é só Instagram ou Facebook) ou 'tem'.
export function tipoDeSite(site) {
  const texto = String(site || '').trim();
  if (!texto) return 'nenhum';
  let host = '';
  try {
    host = new URL(texto.includes('://') ? texto : 'http://' + texto).hostname.toLowerCase();
  } catch (erro) {
    return 'tem';
  }
  const rede = ['instagram.com', 'facebook.com'].some((d) => host === d || host.endsWith('.' + d));
  return rede ? 'rede' : 'tem';
}

// O número vem do servidor já como '55' + DDD + celular, só dígitos. Aqui se confere de novo antes
// de montar o link: qualquer coisa fora desse formato não vira link.
const NUMERO_WHATSAPP = /^55[1-9][1-9]9\d{8}$/;
const LIMITE_DO_LINK = 1800;

export function linkWhatsApp(numero, mensagem) {
  if (typeof numero !== 'string' || !NUMERO_WHATSAPP.test(numero)) return null;
  const base = 'https://wa.me/' + numero;
  const texto = String(mensagem || '').trim();
  if (!texto) return { url: base, comMensagem: false };
  const completo = base + '?text=' + encodeURIComponent(texto);
  // Mensagem grande demais para caber no link: abre a conversa sem texto e a pessoa cola.
  return completo.length <= LIMITE_DO_LINK ? { url: completo, comMensagem: true } : { url: base, comMensagem: false };
}

function simplificar(texto) {
  return String(texto || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[_-]+/g, ' ');
}

// Resposta 12 da entrevista (perfil.conformidade.restricoes). Devolve null quando não há o que avisar.
export function avisoDeConformidade(perfil) {
  const bruto = perfil && perfil.conformidade ? perfil.conformidade.restricoes : '';
  const valor = simplificar(bruto);
  if (valor === '' || valor === 'nao') return null;
  if (valor === 'nao sei') return { tipo: 'incerto', detalhe: '' };
  return { tipo: 'regulado', detalhe: String(bruto).trim().replace(/^sim\s*[:,-]?\s*/i, '') };
}

// Nome de arquivo seguro a partir do cabeçalho Content-Disposition.
export function nomeDoArquivo(cabecalho, padrao) {
  const achou = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(String(cabecalho || ''));
  const nome = achou ? achou[1].trim() : '';
  return /^[A-Za-z0-9._-]{1,80}$/.test(nome) && !nome.includes('..') ? nome : (padrao || 'leads');
}

export const FILTROS_PADRAO = { letra: '', status: '', q: '', excluidos: 'nao', busca: '', sem_site: '', celular: '' };

export function filtrosAtivos(filtros) {
  // Chave que falta vale o padrão (não conta como filtro ligado).
  return Object.keys(FILTROS_PADRAO).filter((k) => {
    const valor = (filtros || {})[k];
    return (valor === undefined || valor === null ? FILTROS_PADRAO[k] : String(valor)) !== FILTROS_PADRAO[k];
  });
}

// O que mostrar quando a lista vem vazia.
export function situacaoDaLista({ total, filtros, buscasFeitas }) {
  if (total > 0) return 'lista';
  if (filtrosAtivos(filtros).length) return 'sem-resultado';
  return buscasFeitas ? 'sem-leads-na-lista' : 'nenhuma-busca';
}

export function resumoDaLista(mostrando, total) {
  if (total === 0) return 'Nenhum lead';
  if (mostrando >= total) return `${total} ${plural(total, 'lead', 'leads')}`;
  return `Mostrando ${mostrando} de ${total} leads`;
}

export function quantosFaltam(mostrando, total, pagina) {
  return Math.max(0, Math.min(pagina || PAGINA_LEADS, total - mostrando));
}

// Só http e https viram link clicável. O site e o link do Maps vêm do Google e não são confiáveis:
// "javascript:", "data:", "file:" e afins nunca chegam a um href.
export function urlSegura(url) {
  const texto = String(url || '').trim();
  if (!texto || texto.length > 2000) return null;
  try {
    const u = new URL(texto);
    return (u.protocol === 'https:' || u.protocol === 'http:') && u.hostname ? u.href : null;
  } catch (erro) {
    return null;
  }
}
