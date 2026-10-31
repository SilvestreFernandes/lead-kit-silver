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
        texto: 'Ele pode ter sido fechado. Siga o passo a passo abaixo para ligar de novo e clique em Tentar de novo.' };
    case 'token':
      return { titulo: 'A página ficou desatualizada',
        texto: 'O kit foi reiniciado depois que você abriu esta página. Recarregue a página para continuar.' };
    case 'servidor':
      return { titulo: 'Algo deu errado dentro do kit',
        texto: 'Olhe a janela escura onde o kit está rodando: ela mostra o que aconteceu. Se o problema continuar, feche essa janela e ligue o kit de novo pelo passo a passo.' };
    case 'recusado':
      return { titulo: 'Pedido recusado', texto: mensagemDoServidor || 'O kit recusou este pedido.' };
    default:
      return { titulo: 'Não deu certo', texto: mensagemDoServidor || 'Tente de novo em instantes.' };
  }
}

export { COMANDO_LIGAR_KIT, COMANDO_LIGAR_MOTOR } from './instrucoes.js';

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

// ---------- Buscar

export const LIMITE_TEXTO_BUSCA = 80;
export const ROTULOS_DE_TAMANHO = { rapida: 'Rápida', media: 'Média', ampla: 'Ampla' };

// "Brasília-DF", "Brasília - DF", "Brasília, DF" e "Brasília/DF" viram { cidade, uf }. Outra coisa
// (por exemplo "todo o Brasil") não é cidade e devolve null.
export function parseRegiao(texto, ufs) {
  const achou = /^(.+?)\s*[-,/]\s*([A-Za-z]{2})$/.exec(String(texto || '').trim());
  if (!achou) return null;
  const uf = achou[2].toUpperCase();
  const cidade = achou[1].trim();
  if (!cidade || cidade.length > LIMITE_TEXTO_BUSCA) return null;
  if (ufs && !ufs.includes(uf)) return null;
  return { cidade, uf };
}

// Sugestões tiradas do perfil. A pessoa pode escrever qualquer outra coisa.
export function sugestoesDeCidade(perfil, ufs) {
  const vistos = new Set();
  const saida = [];
  const regioes = perfil && perfil.cliente && perfil.cliente.regioes;
  for (const regiao of (Array.isArray(regioes) ? regioes : [])) {
    const r = parseRegiao(regiao, ufs);
    if (!r) continue;
    const chave = `${r.cidade.toLowerCase()}|${r.uf}`;
    if (vistos.has(chave)) continue;
    vistos.add(chave);
    saida.push({ ...r, rotulo: `${r.cidade}-${r.uf}` });
  }
  return saida.slice(0, 8);
}

export function sugestoesDeCategoria(perfil) {
  const vistos = new Set();
  const saida = [];
  const tipos = perfil && perfil.cliente && perfil.cliente.tipos;
  for (const tipo of (Array.isArray(tipos) ? tipos : [])) {
    const texto = String(tipo || '').trim();
    if (!texto || texto.length > LIMITE_TEXTO_BUSCA || vistos.has(texto.toLowerCase())) continue;
    vistos.add(texto.toLowerCase());
    saida.push(texto);
  }
  return saida.slice(0, 12);
}

// Confere o formulário antes de enviar. Devolve { campo: mensagem } só dos campos com problema.
export function validarBusca({ categoria, cidade, uf }, ufs) {
  const erros = {};
  const c = String(categoria || '').trim();
  const d = String(cidade || '').trim();
  if (!c) erros.categoria = 'Escreva o tipo de negócio que você quer procurar. Exemplo: padaria.';
  else if (c.length > LIMITE_TEXTO_BUSCA) erros.categoria = `O tipo de negócio está grande demais (no máximo ${LIMITE_TEXTO_BUSCA} letras).`;
  if (!d) erros.cidade = 'Escreva o nome da cidade.';
  else if (d.length > LIMITE_TEXTO_BUSCA) erros.cidade = `O nome da cidade está grande demais (no máximo ${LIMITE_TEXTO_BUSCA} letras).`;
  if (!uf || (ufs && !ufs.includes(uf))) erros.uf = 'Escolha o estado.';
  return erros;
}

export function formatarDuracao(segundos) {
  const total = Math.max(0, Math.round(Number(segundos) || 0));
  if (total < 60) return `${total} s`;
  const minutos = Math.floor(total / 60);
  const resto = total % 60;
  if (minutos < 60) return resto ? `${minutos} min ${resto} s` : `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  return `${horas} h ${minutos % 60} min`;
}

// Quanto durou uma busca terminada, em segundos, ou null.
export function duracaoDaBusca(busca) {
  if (!busca || !busca.criada_em || !busca.terminou_em) return null;
  const inicio = Date.parse(busca.criada_em);
  const fim = Date.parse(busca.terminou_em);
  return Number.isNaN(inicio) || Number.isNaN(fim) || fim < inicio ? null : Math.round((fim - inicio) / 1000);
}

// "hoje às 14:32", "ontem às 09:05" ou "28/10 às 16:40".
export function quandoFoi(iso, agora) {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '';
  const ref = agora || new Date();
  const dois = (n) => String(n).padStart(2, '0');
  const hora = `${dois(data.getHours())}:${dois(data.getMinutes())}`;
  const dia = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
  const ontem = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate() - 1);
  if (dia(data) === dia(ref)) return `hoje às ${hora}`;
  if (dia(data) === dia(ontem)) return `ontem às ${hora}`;
  return `${dois(data.getDate())}/${dois(data.getMonth() + 1)} às ${hora}`;
}

export function descreverBusca(busca) {
  return `${busca.categoria} em ${busca.cidade}-${busca.uf}`;
}

export const ETAPAS_DA_BUSCA = [
  'Achando a cidade no mapa', 'Enviando a busca ao motor', 'Esperando o motor', 'Lendo os resultados', 'Calculando as notas',
];

// Em qual das ETAPAS_DA_BUSCA a busca está (-1 se ainda não se sabe).
export function indiceDaEtapa(etapa) {
  const texto = String(etapa || '');
  if (texto.startsWith('Achando')) return 0;
  if (texto.startsWith('Enviando')) return 1;
  if (texto.startsWith('Esperando') || texto.startsWith('Pausa')) return 2;
  if (texto.startsWith('Lendo')) return 3;
  if (texto.startsWith('Calculando')) return 4;
  return -1;
}

// Porcentagem pelos pontos já concluídos. Busca de um ponto só não tem como dizer: devolve null
// (a tela mostra uma barra sem fim definido, em vez de inventar um número).
export function percentualDaBusca(busca) {
  if (!busca || !busca.pontos || busca.pontos < 2) return null;
  if (indiceDaEtapa(busca.etapa) === 4) return 100;
  const atual = Math.max(1, busca.ponto || 1);
  return Math.round(((atual - 1) / busca.pontos) * 100);
}

export const DICAS_DE_RESULTADO_ZERO = [
  'Confira se o nome da cidade e o estado estão certos.',
  'Tente outro termo, mais comum ou mais simples. Por exemplo, "padaria" em vez de "panificadora".',
  'Tente de novo daqui a alguns minutos. O Google nem sempre responde igual.',
  'Se acontecer com várias cidades e vários termos, o Google pode ter mudado a página e o kit pode precisar de uma atualização. Nesse caso, procure uma versão mais nova do kit.',
];

const ERROS_DA_BUSCA = {
  cidade: ['Não achei essa cidade',
    'Confira o nome da cidade e o estado. Use o nome como aparece no mapa, por exemplo "Brasília" e "DF".'],
  servico_de_mapas: ['Não consegui falar com o serviço de localização',
    'O kit usa esse serviço só para achar a cidade no mapa. Confira a sua conexão com a internet e tente de novo.'],
  motor: ['O motor de busca não respondeu',
    'Confira se o Docker e o motor estão ligados (o aviso no topo mostra o que fazer) e tente de novo.'],
  formato: ['O motor devolveu o resultado num formato que o kit não conhece',
    'O motor pode ter sido atualizado ou o Google pode ter mudado. Se o erro se repetir, o kit precisa de uma atualização. Nada seu foi perdido.'],
  parcial: ['A busca parou no meio',
    'O que já tinha chegado foi salvo e está em Leads. Você pode ver esses leads agora e refazer a busca mais tarde.'],
  interrompida: ['A busca foi interrompida',
    'O kit foi fechado enquanto ela rodava. Abra o kit de novo e refaça a busca. O que já tinha sido salvo continua em Leads.'],
};

export function textoDoErroDaBusca(busca) {
  const achado = ERROS_DA_BUSCA[busca && busca.erro_tipo];
  if (achado) return { titulo: achado[0], dica: achado[1] };
  return { titulo: 'Algo deu errado na busca',
    dica: 'Olhe a janela escura onde o kit está rodando: ela mostra o que aconteceu. Tente de novo. Se repetir, o kit pode precisar de uma atualização.' };
}

// O que mostrar quando uma busca termina. tipo: 'sucesso' | 'vazio' | 'parcial' | 'erro'.
// Resultado zero NUNCA é sucesso. As contagens vêm do servidor: novos, ja_existiam e fora_da_lista.
export function resumoDaBusca(busca) {
  const total = busca.total_leads || 0;
  const duracao = duracaoDaBusca(busca);
  const tempo = duracao === null ? '' : `A busca levou ${formatarDuracao(duracao)}.`;
  if (busca.status === 'erro') {
    const { titulo, dica } = textoDoErroDaBusca(busca);
    const parcial = busca.erro_tipo === 'parcial';
    return { tipo: parcial ? 'parcial' : 'erro', titulo, texto: dica, detalhe: busca.erro || '',
      linhas: parcial ? linhasDeContagem(busca) : [], dicas: [], tempo, temLeads: total > 0 };
  }
  if (total === 0) {
    return { tipo: 'vazio', titulo: 'Nenhum negócio encontrado',
      texto: 'A busca terminou, mas não trouxe nenhum negócio. Isto não é um sucesso: pode ser a cidade, o termo da busca ou uma mudança no Google.',
      detalhe: '', linhas: [], dicas: DICAS_DE_RESULTADO_ZERO.slice(), tempo, temLeads: false };
  }
  return { tipo: 'sucesso', titulo: `Busca concluída: ${total} ${plural(total, 'negócio encontrado', 'negócios encontrados')}`,
    texto: '', detalhe: '', linhas: linhasDeContagem(busca), dicas: [], tempo, temLeads: true };
}

function linhasDeContagem(busca) {
  const { novos, ja_existiam: jaExistiam, fora_da_lista: fora } = busca;
  const linhas = [];
  if (novos !== null && novos !== undefined) {
    linhas.push(`${novos} ${plural(novos, 'negócio novo', 'negócios novos')}, que ainda não estavam no kit.`);
  }
  if (jaExistiam !== null && jaExistiam !== undefined) {
    linhas.push(`${jaExistiam} ${plural(jaExistiam, 'já existia', 'já existiam')} de buscas anteriores.`);
  }
  if (fora !== null && fora !== undefined) {
    linhas.push(fora === 0
      ? 'Nenhum ficou fora da lista pelas exclusões do seu perfil.'
      : `${fora} ${plural(fora, 'ficou fora da lista', 'ficaram fora da lista')} pelas exclusões do seu perfil (por exemplo, sem telefone ou possível rede).`);
  }
  if (novos === 0 && (busca.total_leads || 0) > 0) linhas.push('Nenhum negócio novo: todos já estavam no kit.');
  return linhas;
}
