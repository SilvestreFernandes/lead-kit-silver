// Funções puras da tela Minha oferta: montar o rascunho a partir do perfil, conferir, limpar e calcular.
// Nada aqui mexe na página nem na rede, então dá para testar sem navegador.

const MARCADOR = /\{([^{}]*)\}/g;

export const ROTULOS_DE_MARCADOR = {
  nome: 'nome do negócio',
  cidade: 'cidade',
  categoria: 'tipo do negócio',
  motivo: 'motivo da nota',
  meu_nome: 'seu nome',
  minha_empresa: 'sua empresa',
};

export const ROTULOS_DE_CANAL = { whatsapp: 'WhatsApp', email: 'E-mail', ligacao: 'Ligação', visita: 'Visita' };
export const ROTULOS_DE_TOM = { amigavel: 'Amigável', direto: 'Direto', formal: 'Formal' };
export const ROTULOS_DE_PORTE = { pequeno: 'Pequeno', medio: 'Médio', grande: 'Grande', qualquer: 'Qualquer' };
export const ROTULOS_DE_ATENDIMENTO = { presencial: 'Presencial', remoto: 'Remoto', ambos: 'Os dois' };
// Canais que têm modelo de mensagem pronto. Ligação e visita não têm texto para enviar.
export const CANAIS_COM_MODELO = ['whatsapp', 'email'];

export const LIMITE_DO_TEXTO = 200;
export const LIMITE_DA_OFERTA = 300;
export const LIMITE_DO_MODELO = 1200;

export function copiar(valor) {
  return JSON.parse(JSON.stringify(valor));
}

export function mudou(a, b) {
  return JSON.stringify(a) !== JSON.stringify(b);
}

const texto = (v) => (typeof v === 'string' ? v : '');
const lista = (v) => (Array.isArray(v) ? v.filter((i) => typeof i === 'string') : []);

// Deixa o perfil com todos os campos que a tela edita, sem perder o que a tela não conhece.
export function rascunhoDoPerfil(perfil) {
  const p = copiar(perfil && typeof perfil === 'object' ? perfil : {});
  p.versao = p.versao || 1;
  const negocio = p.negocio || {};
  p.negocio = { ...negocio, nome: texto(negocio.nome), empresa: texto(negocio.empresa), oferta: texto(negocio.oferta),
    atendimento: texto(negocio.atendimento) };
  const cliente = p.cliente || {};
  p.cliente = { ...cliente, tipos: lista(cliente.tipos), regioes: lista(cliente.regioes), porte: texto(cliente.porte),
    exemplo: texto(cliente.exemplo) };
  const pont = p.pontuacao || {};
  p.pontuacao = { ...pont, regras: (Array.isArray(pont.regras) ? pont.regras : [])
    .filter((r) => r && typeof r.id === 'string').map((r) => ({ id: r.id, peso: Number(r.peso) })) };
  p.exclusoes = lista(p.exclusoes);
  p.exclusoes_concorrentes = lista(p.exclusoes_concorrentes);
  p.exclusoes_categorias = lista(p.exclusoes_categorias);
  const ab = p.abordagem || {};
  p.abordagem = { ...ab, canais: lista(ab.canais), tom: texto(ab.tom), oferta_entrada: texto(ab.oferta_entrada),
    volume_semana: texto(ab.volume_semana) };
  p.conformidade = { ...(p.conformidade || {}), restricoes: texto((p.conformidade || {}).restricoes) };
  p.mensagens = { ...(p.mensagens && typeof p.mensagens === 'object' ? p.mensagens : {}) };
  return p;
}

// ---------- listas de texto (tipos de negócio, regiões, concorrentes, categorias)

const chave = (t) => t.trim().toLowerCase();

export function adicionarNaLista(itens, novo) {
  const limpo = texto(novo).replace(/\s+/g, ' ').trim().slice(0, LIMITE_DO_TEXTO);
  if (!limpo || itens.some((i) => chave(i) === chave(limpo))) return itens;
  return [...itens, limpo];
}

export function removerDaLista(itens, indice) {
  return itens.filter((_, i) => i !== indice);
}

// ---------- resposta 12: "não", "não sei" ou "sim: qual"

export function restricaoParaForm(valor) {
  const bruto = texto(valor).trim();
  const simples = bruto.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  if (simples === '' || simples === 'nao') return { resposta: 'nao', detalhe: '' };
  if (simples === 'nao sei') return { resposta: 'nao sei', detalhe: '' };
  return { resposta: 'sim', detalhe: bruto.replace(/^sim\s*[:,-]?\s*/i, '') };
}

export function restricaoParaPerfil({ resposta, detalhe }) {
  if (resposta === 'sim') return detalhe.trim() ? `sim: ${detalhe.trim()}` : 'sim';
  return resposta === 'nao sei' ? 'nao sei' : 'nao';
}

// ---------- importância de cada regra: Ignorar, Pouco, Importa, Muito (o esquema aceita de 0 a 5)

export const NIVEIS_DE_PESO = [
  { id: 'ignorar', rotulo: 'Ignorar', peso: 0 },
  { id: 'pouco', rotulo: 'Pouco', peso: 1 },
  { id: 'importa', rotulo: 'Importa', peso: 2 },
  { id: 'muito', rotulo: 'Muito', peso: 3 },
];

// Peso 4 ou 5 (feito à mão no arquivo ou pela IA) não tem nome: aparece como "Personalizado" e o valor não se perde.
export function nivelDoPeso(peso) {
  const n = NIVEIS_DE_PESO.find((x) => x.peso === peso);
  return n ? n.id : 'personalizado';
}

// Qual botão fica marcado em uma regra, e se aparece o "Personalizado". Decisão pura: a tela só obedece.
// `marcado` é um de ignorar, pouco, importa, muito ou personalizado. Peso 4 ou 5 mostra "Personalizado: N".
export function estadoDosNiveis(regras, id) {
  const peso = pesoDaRegra(regras, id);
  const marcado = nivelDoPeso(peso);
  const personalizado = marcado === 'personalizado';
  return { peso, marcado, personalizado, rotuloPersonalizado: personalizado ? String(peso) : '' };
}

// Aplica o estado acima aos botões da regra. `controles` tem um objeto por nível (ignorar, pouco, importa, muito, personalizado)
// com `checked` e `hidden`, e `textoPersonalizado` com `textContent`. Cada botão recebe um valor explícito, para
// nunca sobrar mais de um marcado nem nenhum.
export function marcarNiveis(controles, estado) {
  for (const n of NIVEIS_DE_PESO) controles[n.id].checked = estado.marcado === n.id;
  controles.personalizado.checked = estado.personalizado;
  controles.personalizado.hidden = !estado.personalizado;
  controles.rotuloPersonalizado.hidden = !estado.personalizado;
  controles.textoPersonalizado.textContent = estado.rotuloPersonalizado;
  return estado;
}

// Regra que não está no perfil conta como peso 0: dá exatamente a mesma nota (testado no kit).
export function pesoDaRegra(regras, id) {
  const r = regras.find((x) => x.id === id);
  return r ? r.peso : 0;
}

// Devolve a lista de regras com o nível novo. Só a regra mexida muda; as outras ficam como estavam.
// "Ignorar" tira a regra da lista, a não ser que o perfil original já a guardasse com peso 0.
export function definirNivel(regras, id, nivel, original = []) {
  const n = NIVEIS_DE_PESO.find((x) => x.id === nivel);
  if (!n) return regras;
  const existe = regras.some((r) => r.id === id);
  if (n.peso === 0) {
    const eraZero = original.some((r) => r.id === id && r.peso === 0);
    if (eraZero) return existe ? regras.map((r) => (r.id === id ? { ...r, peso: 0 } : r)) : [...regras, { id, peso: 0 }];
    return regras.filter((r) => r.id !== id);
  }
  return existe ? regras.map((r) => (r.id === id ? { ...r, peso: n.peso } : r)) : [...regras, { id, peso: n.peso }];
}

// ---------- etapas da tela

export const ETAPAS = [
  { id: 1, nome: 'Sobre você' },
  { id: 2, nome: 'Quem atender' },
  { id: 3, nome: 'O que importa' },
  { id: 4, nome: 'O que evitar' },
  { id: 5, nome: 'Como falar' },
];

const ETAPA_DO_CAMPO = {
  oferta: 1, nome: 1, empresa: 1, atendimento: 1, exemplo: 1, restricao: 1,
  tipos: 2, regioes: 2, porte: 2,
  pesos: 3, cortes: 3,
  concorrentes: 4, categorias: 4,
  canais: 5, tom: 5, entrada: 5, volume: 5,
};

export function etapaDoCampo(campo) {
  if (String(campo).startsWith('mensagem-')) return 5;
  return ETAPA_DO_CAMPO[campo] || 1;
}

// Em qual etapa mexer para resolver um problema que o servidor descreveu em português.
export function etapaDoErro(mensagem) {
  const m = String(mensagem || '');
  const caminho = /\(([a-z_]+(?:\.[a-z_]+)*)\)/.exec(m);
  if (caminho) {
    const c = caminho[1];
    if (c.startsWith('negocio') || c.startsWith('conformidade')) return 1;
    if (c.startsWith('cliente')) return 2;
    if (c.startsWith('pontuacao')) return 3;
    if (c.startsWith('exclusoes')) return 4;
    if (c.startsWith('abordagem') || c.startsWith('mensagens')) return 5;
  }
  if (/mensagem de|marcador|saída clara|canal desconhecido|tom precisa/i.test(m)) return 5;
  if (/porte do cliente/i.test(m)) return 2;
  if (/regra |peso|cortes/i.test(m)) return 3;
  if (/concorrente|categoria|exclus/i.test(m)) return 4;
  return 1;
}

// ---------- nota

export function somaDosPesos(regras) {
  return regras.reduce((total, r) => total + (Number.isFinite(r.peso) ? r.peso : 0), 0);
}

// Mesma conta do kit (pontuacao.cortes): 70% e 40% da soma dos pesos, arredondando para cima.
export function cortesAutomaticos(soma, cortesPadrao = { a: 0.7, b: 0.4 }) {
  const teto = (numerador) => Math.ceil(numerador / 100);
  return { a: teto(soma * Math.round(cortesPadrao.a * 100)), b: teto(soma * Math.round(cortesPadrao.b * 100)) };
}

export function pesoValido(peso, opcoes) {
  return Number.isInteger(peso) && peso >= opcoes.peso_minimo && peso <= opcoes.peso_maximo;
}

// ---------- mensagens

export function marcadoresDoModelo(modelo) {
  return [...texto(modelo).matchAll(MARCADOR)].map((m) => m[1]);
}

// Troca os marcadores por um negócio de exemplo. Marcador desconhecido fica como está e é devolvido.
export function previaDaMensagem(modelo, exemplo, marcadoresValidos) {
  const desconhecidos = [];
  const saida = texto(modelo).replace(MARCADOR, (inteiro, nome) => {
    if (!marcadoresValidos.includes(nome)) { desconhecidos.push(nome); return inteiro; }
    return exemplo[nome] !== undefined && exemplo[nome] !== '' ? exemplo[nome] : inteiro;
  });
  return { texto: saida, desconhecidos };
}

export function exemploDePrevia(perfil, frasesDeMotivo) {
  return {
    nome: 'Padaria Exemplo',
    cidade: 'Brasília',
    categoria: 'padaria',
    motivo: (frasesDeMotivo && frasesDeMotivo.sem_site) || 'não achei um site no perfil do Google Maps',
    meu_nome: texto(perfil.negocio.nome),
    minha_empresa: texto(perfil.negocio.empresa),
  };
}

// Põe o marcador no lugar do cursor (ou no fim, se não houver cursor).
export function inserirMarcador(modelo, inicio, fim, marcador) {
  const base = texto(modelo);
  const a = Number.isInteger(inicio) ? Math.min(inicio, base.length) : base.length;
  const b = Number.isInteger(fim) ? Math.min(Math.max(fim, a), base.length) : a;
  const novo = `{${marcador}}`;
  return { texto: base.slice(0, a) + novo + base.slice(b), cursor: a + novo.length };
}

// ---------- conferir e limpar antes de salvar

// Devolve [{ campo, mensagem }]. O servidor confere de novo (é ele quem manda); isto só evita o ir e vir.
export function conferirRascunho(rascunho, opcoes) {
  const erros = [];
  const falta = (campo, mensagem) => erros.push({ campo, mensagem });
  if (!rascunho.negocio.oferta.trim()) falta('oferta', 'Escreva o que você vende, em uma frase.');
  if (!rascunho.cliente.tipos.length) falta('tipos', 'Inclua pelo menos um tipo de negócio que você quer atender.');
  if (!rascunho.cliente.regioes.length) falta('regioes', 'Inclua pelo menos um lugar onde você atende.');
  if (!rascunho.abordagem.canais.length) falta('canais', 'Escolha pelo menos um jeito de abordar.');
  if (!rascunho.abordagem.tom) falta('tom', 'Escolha o tom das mensagens.');
  for (const r of rascunho.pontuacao.regras) {
    if (!pesoValido(r.peso, opcoes)) falta('pesos', `O peso precisa ser um número inteiro de ${opcoes.peso_minimo} a ${opcoes.peso_maximo}.`);
  }
  const { corte_a: a, corte_b: b } = rascunho.pontuacao;
  if ((a !== undefined && a !== null) || (b !== undefined && b !== null)) {
    if (!Number.isInteger(a) || !Number.isInteger(b) || !(a > b) || b < 0) falta('cortes', 'O corte da nota A precisa ser maior que o da nota B, e os dois precisam ser números inteiros.');
  }
  if (rascunho.exclusoes.includes('concorrente') && !rascunho.exclusoes_concorrentes.length) {
    falta('concorrentes', 'Você marcou para evitar concorrentes. Inclua o nome de pelo menos um, ou desmarque.');
  }
  if (rascunho.exclusoes.includes('categoria') && !rascunho.exclusoes_categorias.length) {
    falta('categorias', 'Você marcou para evitar categorias. Inclua pelo menos uma, ou desmarque.');
  }
  for (const [canal, modelo] of Object.entries(rascunho.mensagens)) {
    const rotulo = ROTULOS_DE_CANAL[canal] || canal;
    if (modelo.length > LIMITE_DO_MODELO) falta('mensagem-' + canal, `A mensagem de ${rotulo} está muito longa.`);
    for (const m of marcadoresDoModelo(modelo)) {
      if (!opcoes.marcadores.includes(m)) falta('mensagem-' + canal, `A mensagem de ${rotulo} usa {${m}}, que não existe. Use os botões abaixo da mensagem.`);
    }
  }
  return erros;
}

// O perfil que vai para o servidor: textos aparados, listas sem repetição, regras na ordem do kit,
// exclusões sem lista que não vale mais, modelos só para canais escolhidos (os outros ficam guardados).
export function perfilParaSalvar(rascunho, opcoes, original = null) {
  const p = copiar(rascunho);
  for (const campo of ['nome', 'empresa', 'oferta']) p.negocio[campo] = p.negocio[campo].replace(/\s+/g, ' ').trim();
  p.negocio.oferta = p.negocio.oferta.slice(0, LIMITE_DA_OFERTA);
  p.cliente.exemplo = p.cliente.exemplo.trim();
  p.abordagem.oferta_entrada = p.abordagem.oferta_entrada.trim();
  // As regras que já estavam no perfil mantêm o lugar (no empate de pontos, vale a ordem do perfil).
  // As que a pessoa acabou de ligar entram depois, na ordem do kit, para o resultado não depender da ordem dos cliques.
  const ordem = opcoes.regras.map((r) => r.id);
  const antigas = original ? original.pontuacao.regras.map((r) => r.id) : [];
  const validas = p.pontuacao.regras.filter((r) => ordem.includes(r.id));
  p.pontuacao.regras = [
    ...antigas.map((id) => validas.find((r) => r.id === id)).filter(Boolean),
    ...validas.filter((r) => !antigas.includes(r.id)).sort((x, y) => ordem.indexOf(x.id) - ordem.indexOf(y.id)),
  ];
  if (p.pontuacao.corte_a === undefined || p.pontuacao.corte_a === null) {
    delete p.pontuacao.corte_a;
    delete p.pontuacao.corte_b;
  }
  if (!p.exclusoes.includes('concorrente')) p.exclusoes_concorrentes = [];
  if (!p.exclusoes.includes('categoria')) p.exclusoes_categorias = [];
  for (const canal of Object.keys(p.mensagens)) {
    p.mensagens[canal] = p.mensagens[canal].trim();
    if (!p.mensagens[canal]) delete p.mensagens[canal];
  }
  return p;
}

export function resumoDaReavaliacao(resposta) {
  const por = resposta.por_letra || {};
  const n = resposta.leads || 0;
  if (!n) return 'Perfil salvo. Ainda não há leads para dar nota.';
  return `Perfil salvo. ${n} ${n === 1 ? 'lead recebeu' : 'leads receberam'} nota de novo: ${por.A || 0} A, ${por.B || 0} B e ${por.C || 0} C.`;
}
