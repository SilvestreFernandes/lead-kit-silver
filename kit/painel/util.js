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
