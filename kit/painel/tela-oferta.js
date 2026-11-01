// Tela Minha oferta: edita o perfil (as respostas da entrevista), as regras de nota, o que evitar e as mensagens.
// São cinco etapas, todas clicáveis a qualquer momento. Salvar vale de qualquer etapa: grava o perfil e dá nota de
// novo aos leads. Nenhuma IA é chamada aqui: é só um formulário.
import { ler, escrever, ErroApi } from './api.js';
import { el, limpar, blocoEstado, blocoCarregando, cabecalhoDaTela } from './dom.js';
import {
  ROTULOS_DE_MARCADOR, ROTULOS_DE_CANAL, ROTULOS_DE_TOM, ROTULOS_DE_PORTE, ROTULOS_DE_ATENDIMENTO, CANAIS_COM_MODELO,
  LIMITE_DO_TEXTO, LIMITE_DA_OFERTA, LIMITE_DO_MODELO, NIVEIS_DE_PESO, ETAPAS,
  copiar, mudou, rascunhoDoPerfil, adicionarNaLista, removerDaLista, restricaoParaForm, restricaoParaPerfil,
  somaDosPesos, cortesAutomaticos, previaDaMensagem, exemploDePrevia, inserirMarcador, estadoDosNiveis, marcarNiveis, definirNivel,
  etapaDoCampo, etapaDoErro, conferirRascunho, perfilParaSalvar, resumoDaReavaliacao,
} from './oferta-util.js';

export const TEXTO_SALVAR = 'Ao salvar, o painel dá nota de novo a todos os leads com as regras novas. Nenhum lead é apagado e nenhuma mensagem é enviada.';
export const TEXTO_SEM_IA = 'Nada aqui usa IA. Os textos ficam salvos só no seu computador, e o painel apenas troca os marcadores pelos dados de cada negócio.';
export const DURACAO_DO_TUDO_SALVO_MS = 8000;

// O que a pessoa editou e ainda não salvou fica guardado enquanto a página estiver aberta,
// para não perder nada ao trocar de aba. Se o perfil mudou no arquivo, o rascunho é descartado.
let pendente = null;
// A frase de "tudo salvo" é curta e temporária. Fica guardada fora da tela porque, ao salvar, o kit pode passar a
// ver o perfil como válido e a tela é montada de novo.
let ultimoResultado = { texto: '', ate: 0 };
let ultimaEtapa = 1;

export function descartarRascunhoGuardado() {
  pendente = null;
  ultimoResultado = { texto: '', ate: 0 };
  ultimaEtapa = 1;
}

export function montarOferta(raiz, ctx) {
  const recado = ctx.consumirParametros ? ctx.consumirParametros() : null;
  const estado = {
    opcoes: null, original: null, rascunho: null, errosDoPerfil: [], avisosDoPerfil: [],
    erros: [], errosDoServidor: [], salvando: false, carregando: true, erro: null,
    etapa: recado && recado.etapa >= 1 && recado.etapa <= ETAPAS.length ? recado.etapa : ultimaEtapa,
  };
  let vivo = true;
  let temporizadorDoSalvo = null;
  const ref = { ouvintes: [] };

  const anuncio = el('div', { class: 'so-leitor', role: 'status', 'aria-live': 'polite' });
  const salvo = el('p', { class: 'tudo-salvo', role: 'status', hidden: true });
  const area = el('div', {});
  raiz.append(
    cabecalhoDaTela('Minha oferta', 'Conte o que você vende e como prefere falar. É com isso que o painel dá nota aos negócios e escreve as mensagens.'),
    el('p', { class: 'hint texto-fixo' }, TEXTO_SALVAR),
    anuncio, salvo, area);

  const sujo = () => !!estado.rascunho && mudou(estado.rascunho, estado.original);
  const avisoDeSaida = (evento) => { if (sujo()) { evento.preventDefault(); evento.returnValue = ''; } };
  window.addEventListener('beforeunload', avisoDeSaida);

  function anunciar(texto) {
    anuncio.textContent = '';
    setTimeout(() => { anuncio.textContent = texto; }, 30);
  }

  function mostrarTudoSalvo() {
    clearTimeout(temporizadorDoSalvo);
    const restante = ultimoResultado.ate - Date.now();
    salvo.hidden = !(ultimoResultado.texto && restante > 0);
    salvo.textContent = salvo.hidden ? '' : ultimoResultado.texto;
    if (!salvo.hidden) temporizadorDoSalvo = setTimeout(() => { salvo.hidden = true; }, restante);
  }

  // ---------- carregar

  async function carregar() {
    estado.carregando = true;
    estado.erro = null;
    desenhar();
    try {
      const [opcoes, resposta] = await Promise.all([ler('/api/opcoes'), ler('/api/perfil').catch((erro) => {
        if (erro instanceof ErroApi && erro.status === 404) return { perfil: {}, erros: [], avisos: [] };
        throw erro;
      })]);
      if (!vivo) return;
      estado.opcoes = opcoes;
      estado.errosDoPerfil = resposta.erros || [];
      estado.avisosDoPerfil = resposta.avisos || [];
      estado.original = rascunhoDoPerfil(resposta.perfil);
      estado.rascunho = pendente && !mudou(pendente.original, estado.original) ? pendente.rascunho : copiar(estado.original);
      if (!(recado && recado.etapa) && estado.errosDoPerfil.length) estado.etapa = etapaDoErro(estado.errosDoPerfil[0]);
      estado.carregando = false;
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (!vivo) return;
      estado.carregando = false;
      estado.erro = erro;
    }
    desenhar();
  }

  // ---------- peças de formulário

  function guardar() {
    pendente = sujo() ? { original: copiar(estado.original), rascunho: copiar(estado.rascunho) } : null;
  }

  function aoMudar() {
    ultimoResultado = { texto: '', ate: 0 };
    mostrarTudoSalvo();
    guardar();
    for (const ouvinte of ref.ouvintes) ouvinte();
  }

  function erroDo(campo) {
    return el('p', { class: 'erro-campo', id: 'erro-' + campo, role: 'alert', hidden: true, dataset: { campo } });
  }

  function campoDeTexto({ id, rotulo, ajuda, obter, definir, longo, limite = LIMITE_DO_TEXTO, placeholder }) {
    const entrada = el(longo ? 'textarea' : 'input', {
      class: 'input' + (longo ? ' area' : ''), id, type: longo ? null : 'text', rows: longo ? '2' : null, maxlength: String(limite),
      placeholder: placeholder || null, autocomplete: 'off', 'aria-describedby': ajuda ? `${id}-ajuda erro-${id}` : 'erro-' + id,
    });
    entrada.value = obter();
    entrada.addEventListener('input', () => { definir(entrada.value); aoMudar(); });
    return el('div', { class: 'field' },
      el('label', { class: 'label', for: id }, rotulo),
      entrada, erroDo(id),
      ajuda ? el('p', { class: 'hint', id: id + '-ajuda' }, ajuda) : null);
  }

  function campoDeEscolha({ id, rotulo, ajuda, opcoes, obter, definir, vazio }) {
    const atual = obter();
    const lista = [...opcoes];
    if (atual && !lista.some(([v]) => v === atual)) lista.push([atual, atual]);  // valor antigo: não perde
    const escolha = el('select', { class: 'select', id, 'aria-describedby': ajuda ? `${id}-ajuda erro-${id}` : 'erro-' + id },
      vazio ? el('option', { value: '' }, vazio) : null,
      lista.map(([valor, texto]) => el('option', { value: valor, selected: valor === atual || null }, texto)));
    escolha.addEventListener('change', () => { definir(escolha.value); aoMudar(); });
    return el('div', { class: 'field' },
      el('label', { class: 'label', for: id }, rotulo), escolha, erroDo(id),
      ajuda ? el('p', { class: 'hint', id: id + '-ajuda' }, ajuda) : null);
  }

  // Lista de textos com chips que se removem e um campo para incluir.
  function campoDeLista({ id, rotulo, ajuda, placeholder, obter, definir, botao = 'Incluir' }) {
    const chips = el('div', { class: 'chips', 'aria-label': rotulo });
    const entrada = el('input', { class: 'input', id, type: 'text', maxlength: String(LIMITE_DO_TEXTO), autocomplete: 'off',
      placeholder: placeholder || null, 'aria-describedby': `${id}-ajuda erro-${id}` });
    function desenharChips() {
      limpar(chips);
      const itens = obter();
      itens.forEach((item, i) => chips.append(el('button', {
        class: 'chip chip-x', type: 'button', 'aria-label': `Tirar ${item}`,
        onClick: () => { definir(removerDaLista(obter(), i)); desenharChips(); aoMudar(); anunciar(`${item} foi tirado.`); },
      }, item, el('span', { 'aria-hidden': 'true' }, ' ×'))));
      if (!itens.length) chips.append(el('span', { class: 'hint' }, 'Nada incluído ainda.'));
    }
    function incluir() {
      const novo = adicionarNaLista(obter(), entrada.value);
      if (novo !== obter()) { definir(novo); aoMudar(); desenharChips(); anunciar('Incluído.'); }
      entrada.value = '';
      entrada.focus();
    }
    entrada.addEventListener('keydown', (evento) => { if (evento.key === 'Enter') { evento.preventDefault(); incluir(); } });
    desenharChips();
    return el('div', { class: 'field' },
      el('label', { class: 'label', for: id }, rotulo),
      chips,
      el('div', { class: 'linha-incluir' }, entrada, el('button', { class: 'btn btn-small', type: 'button', onClick: incluir }, botao)),
      erroDo(id),
      el('p', { class: 'hint', id: id + '-ajuda' }, ajuda));
  }

  function grupoDeMarcar({ id, rotulo, ajuda, itens, obter, definir }) {
    return el('fieldset', { class: 'field grupo', 'aria-describedby': `${id}-ajuda erro-${id}`, dataset: { foco: id } },
      el('legend', { class: 'label' }, rotulo),
      el('div', { class: 'chips' }, itens.map(([valor, texto]) => {
        const marcado = () => obter().includes(valor);
        const botao = el('button', { class: 'chip', type: 'button', 'aria-pressed': String(marcado()) }, texto);
        botao.addEventListener('click', () => {
          definir(marcado() ? obter().filter((v) => v !== valor) : [...obter(), valor]);
          botao.setAttribute('aria-pressed', String(marcado()));
          aoMudar();
        });
        return botao;
      })),
      erroDo(id),
      ajuda ? el('p', { class: 'hint', id: id + '-ajuda' }, ajuda) : null);
  }

  // ---------- etapas

  function painel(numero, titulo, ...conteudo) {
    return el('section', { class: 'card painel-etapa', id: 'etapa-' + numero, hidden: numero !== estado.etapa || null, 'aria-labelledby': 'titulo-etapa-' + numero },
      el('h2', { id: 'titulo-etapa-' + numero, tabindex: '-1' }, `Etapa ${numero} de ${ETAPAS.length}: ${titulo}`),
      ...conteudo);
  }

  function etapa1() {
    const r = estado.rascunho;
    const atual = restricaoParaForm(r.conformidade.restricoes);
    const detalhe = el('input', { class: 'input', id: 'restricao-detalhe', type: 'text', maxlength: String(LIMITE_DO_TEXTO),
      placeholder: 'Qual? Exemplo: conselho de classe', value: atual.detalhe, 'aria-label': 'Qual regra' });
    const escolha = el('select', { class: 'select', id: 'restricao' },
      el('option', { value: 'nao', selected: atual.resposta === 'nao' || null }, 'Não'),
      el('option', { value: 'sim', selected: atual.resposta === 'sim' || null }, 'Sim'),
      el('option', { value: 'nao sei', selected: atual.resposta === 'nao sei' || null }, 'Não sei'));
    function sincronizar() {
      detalhe.hidden = escolha.value !== 'sim';
      r.conformidade.restricoes = restricaoParaPerfil({ resposta: escolha.value, detalhe: detalhe.value });
    }
    escolha.addEventListener('change', () => { sincronizar(); aoMudar(); });
    detalhe.addEventListener('input', () => { sincronizar(); aoMudar(); });
    detalhe.hidden = atual.resposta !== 'sim';
    return painel(1, ETAPAS[0].nome,
      campoDeTexto({ id: 'oferta', rotulo: 'O que você vende, em uma frase', longo: true, limite: LIMITE_DA_OFERTA,
        placeholder: 'Exemplo: sites e automações com IA para negócios locais',
        obter: () => r.negocio.oferta, definir: (v) => { r.negocio.oferta = v; } }),
      el('div', { class: 'row-duas' },
        campoDeTexto({ id: 'nome', rotulo: 'Seu nome', obter: () => r.negocio.nome, definir: (v) => { r.negocio.nome = v; } }),
        campoDeTexto({ id: 'empresa', rotulo: 'Sua empresa (se tiver)', obter: () => r.negocio.empresa, definir: (v) => { r.negocio.empresa = v; } })),
      campoDeEscolha({ id: 'atendimento', rotulo: 'Como você atende', vazio: 'Não informado',
        opcoes: estado.opcoes.atendimentos.map((a) => [a, ROTULOS_DE_ATENDIMENTO[a] || a]),
        obter: () => r.negocio.atendimento, definir: (v) => { r.negocio.atendimento = v; } }),
      campoDeTexto({ id: 'exemplo', rotulo: 'Seu melhor cliente até hoje (opcional)', longo: true,
        ajuda: 'Só ajuda a lembrar quem funciona bem para você. Não muda a nota.',
        obter: () => r.cliente.exemplo, definir: (v) => { r.cliente.exemplo = v; } }),
      el('div', { class: 'field' },
        el('label', { class: 'label', for: 'restricao' }, 'Sua área tem regras de publicidade ou de abordagem?'),
        escolha, detalhe,
        el('p', { class: 'hint' }, 'Se a resposta for sim ou não sei, a tela Leads mostra um aviso fixo. O kit não confere se uma mensagem cumpre regra nenhuma, e isto não é aconselhamento jurídico.')));
  }

  function etapa2() {
    const r = estado.rascunho;
    return painel(2, ETAPAS[1].nome,
      campoDeLista({ id: 'tipos', rotulo: 'Tipos de negócio', placeholder: 'Exemplo: padaria',
        ajuda: 'Aparecem como sugestão na tela Buscar. Aperte Enter para incluir.',
        obter: () => r.cliente.tipos, definir: (v) => { r.cliente.tipos = v; } }),
      campoDeLista({ id: 'regioes', rotulo: 'Onde você atende', placeholder: 'Exemplo: Brasília-DF',
        ajuda: 'Escreva como Cidade-UF, por exemplo Sobradinho-DF. Também aparecem como sugestão na tela Buscar.',
        obter: () => r.cliente.regioes, definir: (v) => { r.cliente.regioes = v; } }),
      campoDeEscolha({ id: 'porte', rotulo: 'Tamanho do negócio que você procura', vazio: 'Não informado',
        opcoes: Object.entries(ROTULOS_DE_PORTE),
        obter: () => r.cliente.porte, definir: (v) => { r.cliente.porte = v; } }));
  }

  // Uma regra de nota: "Quanto importa?" com quatro escolhas. Peso 4 ou 5 aparece como Personalizado.
  function linhaDaRegra(regra) {
    const r = estado.rascunho;
    const nome = `peso-${regra.id}`;
    const grupo = el('div', { class: 'seg seg-peso', role: 'radiogroup', 'aria-label': `Quanto importa: ${regra.texto}` });
    const controles = {};
    for (const n of NIVEIS_DE_PESO) {
      const entrada = el('input', { type: 'radio', name: nome, id: `${nome}-${n.id}`, value: n.id });
      entrada.addEventListener('change', () => {
        if (!entrada.checked) return;
        r.pontuacao.regras = definirNivel(r.pontuacao.regras, regra.id, n.id, estado.original.pontuacao.regras);
        sincronizar();
        aoMudar();
      });
      controles[n.id] = entrada;
      grupo.append(entrada, el('label', { for: `${nome}-${n.id}` }, el('b', {}, n.rotulo)));
    }
    controles.personalizado = el('input', { type: 'radio', name: nome, id: `${nome}-personalizado`, value: 'personalizado' });
    controles.textoPersonalizado = el('b', { class: 'num' }, '');
    controles.rotuloPersonalizado = el('label', { for: `${nome}-personalizado` }, el('b', {}, 'Personalizado: '), controles.textoPersonalizado);
    grupo.append(controles.personalizado, controles.rotuloPersonalizado);
    // Quem decide o que fica marcado é estadoDosNiveis (função pura, testada); aqui só se aplica o resultado.
    function sincronizar() {
      const e = marcarNiveis(controles, estadoDosNiveis(r.pontuacao.regras, regra.id));
      grupo.classList.toggle('com-personalizado', e.personalizado);
    }
    sincronizar();
    return el('div', { class: 'regra' },
      el('div', { class: 'regra-texto' }, el('b', {}, regra.texto.charAt(0).toUpperCase() + regra.texto.slice(1)), el('span', {}, regra.descricao)),
      grupo);
  }

  function etapa3() {
    const r = estado.rascunho;
    const opcoes = estado.opcoes;
    const resumo = el('p', { class: 'resumo-corte', role: 'status' });
    const manual = el('div', { class: 'cortes-manuais', hidden: true });
    const campoA = el('input', { class: 'input num-curto', id: 'corte-a', type: 'number', min: '1', step: '1', 'aria-describedby': 'erro-cortes' });
    const campoB = el('input', { class: 'input num-curto', id: 'corte-b', type: 'number', min: '0', step: '1', 'aria-describedby': 'erro-cortes' });
    const automatico = el('input', { type: 'checkbox', id: 'corte-auto', checked: (r.pontuacao.corte_a === undefined || r.pontuacao.corte_a === null) || null });

    function atualizarCortes() {
      const soma = somaDosPesos(r.pontuacao.regras);
      const auto = cortesAutomaticos(soma, opcoes.cortes_padrao);
      manual.hidden = automatico.checked;
      if (automatico.checked) {
        delete r.pontuacao.corte_a;
        delete r.pontuacao.corte_b;
        resumo.textContent = soma
          ? `Com estas escolhas, o máximo é ${soma} pontos. Nota A: ${auto.a} ou mais. Nota B: ${auto.b} ou mais. Abaixo disso, nota C.`
          : 'Escolha pelo menos uma coisa que importa para os negócios receberem nota.';
      } else {
        const a = Number.parseInt(campoA.value, 10);
        const b = Number.parseInt(campoB.value, 10);
        r.pontuacao.corte_a = Number.isNaN(a) ? null : a;
        r.pontuacao.corte_b = Number.isNaN(b) ? null : b;
        resumo.textContent = `O máximo é ${soma} pontos. Nota A: ${campoA.value || '?'} ou mais. Nota B: ${campoB.value || '?'} ou mais.`;
      }
    }
    campoA.value = r.pontuacao.corte_a ?? '';
    campoB.value = r.pontuacao.corte_b ?? '';
    automatico.addEventListener('change', () => {
      if (!automatico.checked) {
        const auto = cortesAutomaticos(somaDosPesos(r.pontuacao.regras), opcoes.cortes_padrao);
        campoA.value = campoA.value || String(auto.a);
        campoB.value = campoB.value || String(auto.b);
      }
      atualizarCortes();
      aoMudar();
    });
    for (const campo of [campoA, campoB]) campo.addEventListener('input', () => { atualizarCortes(); aoMudar(); });
    ref.ouvintes.push(atualizarCortes);
    manual.append(
      el('label', { class: 'peso-rotulo', for: 'corte-a' }, el('span', {}, 'Nota A a partir de'), campoA),
      el('label', { class: 'peso-rotulo', for: 'corte-b' }, el('span', {}, 'Nota B a partir de'), campoB));
    atualizarCortes();

    return painel(3, ETAPAS[2].nome,
      el('p', { class: 'hint' }, 'Diga o quanto cada coisa importa para você. O painel soma os pontos e mostra a nota A, B ou C de cada negócio. Os valores iniciais são um ponto de partida: ajuste com o que você vê funcionar.'),
      el('div', { class: 'regras' }, opcoes.regras.map(linhaDaRegra)),
      erroDo('pesos'),
      el('div', { class: 'field cortes' },
        el('label', { class: 'check', for: 'corte-auto' }, automatico,
          el('div', {}, el('b', {}, 'Deixar o painel calcular as notas A, B e C'), el('span', {}, 'Recomendado. A nota A é para quem soma 70% dos pontos possíveis ou mais, e a B para 40% ou mais.'))),
        manual, erroDo('cortes'), resumo));
  }

  function etapa4() {
    const r = estado.rascunho;
    const lista = estado.opcoes.exclusoes;
    const concorrentes = campoDeLista({ id: 'concorrentes', rotulo: 'Concorrentes a evitar', placeholder: 'Nome ou site, exemplo: Agência Tal',
      ajuda: 'Negócios com esse nome, ou com esse site, saem da lista.',
      obter: () => r.exclusoes_concorrentes, definir: (v) => { r.exclusoes_concorrentes = v; } });
    const categorias = campoDeLista({ id: 'categorias', rotulo: 'Categorias a evitar', placeholder: 'Exemplo: igreja',
      ajuda: 'Negócios com esse tipo no Google Maps saem da lista.',
      obter: () => r.exclusoes_categorias, definir: (v) => { r.exclusoes_categorias = v; } });
    function mostrar() {
      concorrentes.hidden = !r.exclusoes.includes('concorrente');
      categorias.hidden = !r.exclusoes.includes('categoria');
    }
    ref.ouvintes.push(mostrar);
    mostrar();
    return painel(4, ETAPAS[3].nome,
      el('p', { class: 'hint' }, 'Quem se encaixa aqui sai da lista principal, mas não é apagado. Dá para ver em Leads, no filtro de excluídos, com o motivo.'),
      el('div', { class: 'field grupo' },
        lista.map((ex) => {
          const marcar = el('input', { type: 'checkbox', id: 'ex-' + ex.id, checked: r.exclusoes.includes(ex.id) || null });
          marcar.addEventListener('change', () => {
            r.exclusoes = marcar.checked ? [...r.exclusoes, ex.id] : r.exclusoes.filter((v) => v !== ex.id);
            aoMudar();
          });
          return el('label', { class: 'check', for: 'ex-' + ex.id }, marcar,
            el('div', {}, el('b', {}, ex.texto.charAt(0).toUpperCase() + ex.texto.slice(1)), el('span', {}, ex.descricao)));
        })),
      concorrentes, categorias);
  }

  function mensagens() {
    const r = estado.rascunho;
    const opcoes = estado.opcoes;
    const corpo = el('div', { class: 'mensagens' });
    function canaisVisiveis() {
      return CANAIS_COM_MODELO.filter((c) => r.abordagem.canais.includes(c) || r.mensagens[c]);
    }
    function modelo(canal) {
      const rotulo = ROTULOS_DE_CANAL[canal];
      const id = 'mensagem-' + canal;
      const area = el('textarea', { class: 'input area-mensagem', id, rows: canal === 'email' ? '8' : '6', maxlength: String(LIMITE_DO_MODELO),
        'aria-describedby': `${id}-ajuda erro-${id} previa-${canal}` });
      area.value = r.mensagens[canal] || '';
      const previa = el('div', { class: 'previa', id: 'previa-' + canal });
      const avisoPrevia = el('p', { class: 'erro-campo', hidden: true });
      function desenharPrevia() {
        const exemplo = exemploDePrevia(r, opcoes.frases_de_motivo);
        const { texto, desconhecidos } = previaDaMensagem(area.value || opcoes.modelos_padrao[canal], exemplo, opcoes.marcadores);
        limpar(previa);
        previa.append(el('small', {}, area.value ? 'Como fica para um negócio de exemplo' : 'Modelo padrão, como fica para um negócio de exemplo'),
          ...texto.split('\n').map((linha) => el('p', {}, linha)));
        avisoPrevia.hidden = !desconhecidos.length;
        avisoPrevia.textContent = desconhecidos.length ? `{${desconhecidos[0]}} não existe. Use os botões abaixo para incluir só o que o painel conhece.` : '';
      }
      area.addEventListener('input', () => { r.mensagens[canal] = area.value; desenharPrevia(); aoMudar(); });
      const botoesDeMarcador = opcoes.marcadores.map((m) => el('button', { class: 'chip', type: 'button',
        title: `Inclui {${m}} na mensagem`, onClick: () => {
          const { texto, cursor } = inserirMarcador(area.value, area.selectionStart, area.selectionEnd, m);
          area.value = texto;
          r.mensagens[canal] = texto;
          area.focus();
          area.setSelectionRange(cursor, cursor);
          desenharPrevia();
          aoMudar();
        } }, ROTULOS_DE_MARCADOR[m] || m));
      desenharPrevia();
      return el('div', { class: 'field' },
        el('label', { class: 'label', for: id }, `Mensagem de ${rotulo}`),
        area,
        el('p', { class: 'hint', id: id + '-ajuda' }, 'Deixe em branco para usar o modelo padrão. Inclua o que muda em cada negócio com os botões:'),
        el('div', { class: 'chips', 'aria-label': 'Incluir na mensagem' }, botoesDeMarcador),
        erroDo(id), avisoPrevia, previa,
        el('div', { class: 'acoes' },
          el('button', { class: 'btn btn-small', type: 'button', onClick: () => {
            r.mensagens[canal] = '';
            area.value = '';
            desenharPrevia();
            aoMudar();
            anunciar('Voltou ao modelo padrão.');
          } }, 'Usar o modelo padrão')));
    }
    function desenharCorpo() {
      limpar(corpo);
      const canais = canaisVisiveis();
      corpo.append(...(canais.length ? canais.map(modelo)
        : [el('p', { class: 'hint' }, 'Escolha WhatsApp ou e-mail em "Canais" para escrever uma mensagem.')]));
    }
    let ultimos = '';
    ref.ouvintes.push(() => {
      const chave = canaisVisiveis().join();
      if (chave !== ultimos) { ultimos = chave; desenharCorpo(); }
    });
    ultimos = canaisVisiveis().join();
    desenharCorpo();
    return el('div', { class: 'bloco-mensagens' },
      el('h3', {}, 'Mensagens de abordagem'),
      el('p', { class: 'hint' }, 'Toda mensagem precisa dar uma saída clara, por exemplo "se não fizer sentido, é só avisar que não escrevo mais". O painel confere isso ao salvar. A mensagem de cada negócio pode ser editada na tela Leads.'),
      corpo);
  }

  function etapa5() {
    const r = estado.rascunho;
    return painel(5, ETAPAS[4].nome,
      grupoDeMarcar({ id: 'canais', rotulo: 'Canais', ajuda: 'O painel só escreve mensagem para WhatsApp e e-mail. O envio é sempre manual, um negócio por vez.',
        itens: estado.opcoes.canais.map((c) => [c, ROTULOS_DE_CANAL[c] || c]),
        obter: () => r.abordagem.canais, definir: (v) => { r.abordagem.canais = v; } }),
      campoDeEscolha({ id: 'tom', rotulo: 'Tom das mensagens', vazio: 'Escolha',
        opcoes: estado.opcoes.tons.map((t) => [t, ROTULOS_DE_TOM[t] || t]),
        obter: () => r.abordagem.tom, definir: (v) => { r.abordagem.tom = v; } }),
      campoDeTexto({ id: 'entrada', rotulo: 'Sua oferta de entrada', placeholder: 'Exemplo: diagnóstico grátis',
        ajuda: 'O que você oferece no primeiro contato.',
        obter: () => r.abordagem.oferta_entrada, definir: (v) => { r.abordagem.oferta_entrada = v; } }),
      campoDeEscolha({ id: 'volume', rotulo: 'Quantos contatos você consegue fazer por semana', vazio: 'Não informado',
        opcoes: estado.opcoes.volumes_semana.map((v) => [v.id, v.texto]),
        obter: () => r.abordagem.volume_semana, definir: (v) => { r.abordagem.volume_semana = v; } }),
      mensagens());
  }

  // ---------- navegação entre etapas

  const botoesDeEtapa = [];

  function irParaEtapa(numero, { focar = true } = {}) {
    estado.etapa = numero;
    ultimaEtapa = numero;
    ETAPAS.forEach((e) => {
      const painelDaEtapa = area.querySelector('#etapa-' + e.id);
      if (painelDaEtapa) painelDaEtapa.hidden = e.id !== numero;
    });
    atualizarEtapas();
    if (focar) {
      const titulo = area.querySelector(`#titulo-etapa-${numero}`);
      if (titulo) { titulo.focus(); titulo.scrollIntoView({ block: 'start' }); }
      anunciar(`Etapa ${numero} de ${ETAPAS.length}: ${ETAPAS[numero - 1].nome}`);
    }
  }

  function etapasComProblema() {
    const set = new Set();
    for (const e of estado.erros) set.add(etapaDoCampo(e.campo));
    for (const m of [...estado.errosDoServidor, ...estado.errosDoPerfil]) set.add(etapaDoErro(m));
    return set;
  }

  function atualizarEtapas() {
    const problemas = etapasComProblema();
    botoesDeEtapa.forEach((b, i) => {
      const numero = i + 1;
      const atual = numero === estado.etapa;
      if (atual) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
      b.classList.toggle('com-problema', problemas.has(numero));
      b.querySelector('.problema').hidden = !problemas.has(numero);
    });
    if (ref.voltar) ref.voltar.hidden = estado.etapa === 1;
    if (ref.continuar) ref.continuar.hidden = estado.etapa === ETAPAS.length;
    if (ref.salvarFim) ref.salvarFim.hidden = estado.etapa !== ETAPAS.length;
  }

  function nav() {
    botoesDeEtapa.length = 0;
    return el('nav', { class: 'etapas', 'aria-label': 'Etapas do perfil' },
      el('ol', {}, ETAPAS.map((e) => {
        const b = el('button', { class: 'etapa', type: 'button', onClick: () => irParaEtapa(e.id) },
          el('span', { class: 'n', 'aria-hidden': 'true' }, String(e.id)),
          el('span', { class: 'nome' }, e.nome),
          el('span', { class: 'problema', hidden: true }, el('span', { 'aria-hidden': 'true' }, '!'), el('span', { class: 'so-leitor' }, ' (tem um problema)')));
        botoesDeEtapa.push(b);
        return el('li', {}, b);
      })));
  }

  // ---------- salvar

  const barra = {
    no: el('div', { class: 'barra-salvar', role: 'region', 'aria-label': 'Salvar o perfil', hidden: true }),
    texto: el('span', { class: 'barra-texto' }),
    salvar: el('button', { class: 'btn btn-primary', type: 'submit', form: 'form-oferta' }, 'Salvar e dar nota de novo'),
    descartar: el('button', { class: 'btn btn-small btn-quieto', type: 'button' }, 'Descartar mudanças'),
  };
  barra.no.append(barra.texto, barra.descartar, barra.salvar);

  function temAlerta() {
    return estado.erros.length > 0 || estado.errosDoServidor.length > 0;
  }

  function atualizarBarra() {
    const alterado = sujo();
    barra.no.hidden = !(alterado || estado.salvando);
    barra.no.classList.toggle('alerta', temAlerta());
    barra.salvar.disabled = estado.salvando || !alterado;
    barra.descartar.disabled = estado.salvando || !alterado;
    barra.salvar.textContent = estado.salvando ? 'Salvando...' : 'Salvar e dar nota de novo';
    barra.texto.textContent = estado.salvando ? 'Salvando e dando nota de novo...'
      : temAlerta() ? 'Não foi salvo. Veja os avisos no alto da página.' : 'Mudanças ainda não salvas.';
    if (ref.salvarFim) ref.salvarFim.disabled = estado.salvando || !alterado;
    if (temAlerta() || !alterado) barra.no.classList.remove('recolhida');
  }

  // No celular a barra sai da frente ao rolar para baixo e volta ao rolar para cima. Ela só se desloca (nunca some do
  // documento), então um botão dela que receba foco já a traz de volta. Erro ou falha ao salvar a mantêm à vista.
  let ultimoY = window.scrollY || 0;
  const aoRolar = () => {
    const y = window.scrollY || 0;
    const celular = window.matchMedia && window.matchMedia('(max-width: 760px)').matches;
    if (celular && !temAlerta() && !barra.no.contains(document.activeElement)) {
      if (y > ultimoY + 6 && y > 80) barra.no.classList.add('recolhida');
      else if (y < ultimoY - 6 || y <= 80) barra.no.classList.remove('recolhida');
    } else {
      barra.no.classList.remove('recolhida');
    }
    ultimoY = y;
  };
  window.addEventListener('scroll', aoRolar, { passive: true });
  barra.no.addEventListener('focusin', () => barra.no.classList.remove('recolhida'));

  function mostrarErros() {
    const porCampo = new Map();
    for (const e of estado.erros) if (!porCampo.has(e.campo)) porCampo.set(e.campo, e.mensagem);
    for (const no of area.querySelectorAll('.erro-campo[data-campo]')) {
      const mensagem = porCampo.get(no.dataset.campo);
      no.hidden = !mensagem;
      no.textContent = mensagem || '';
    }
    for (const no of area.querySelectorAll('[aria-describedby]')) {
      if (no.id) no.setAttribute('aria-invalid', porCampo.has(no.id) ? 'true' : 'false');
    }
  }

  function focoDoCampo(campo) {
    const direto = area.querySelector('#' + CSS.escape(campo));
    if (direto && direto.focus) return direto;
    if (campo === 'pesos') return area.querySelector('.seg-peso input:checked');
    if (campo === 'cortes') return area.querySelector('#corte-auto');
    return area.querySelector(`[data-foco="${campo}"] button`);
  }

  function desenharResumoDeErros() {
    limpar(ref.erros);
    const itens = [
      ...estado.erros.map((e) => ({ mensagem: e.mensagem, etapa: etapaDoCampo(e.campo), campo: e.campo })),
      ...estado.errosDoServidor.map((m) => ({ mensagem: m, etapa: etapaDoErro(m) })),
    ];
    ref.erros.hidden = !itens.length;
    if (!itens.length) return;
    ref.erros.append(el('b', {}, 'O perfil não foi salvo. Corrija estes pontos:'),
      el('ul', { class: 'lista-erros' }, itens.map((i) => el('li', {}, i.mensagem + ' ',
        el('button', { class: 'btn btn-small', type: 'button', onClick: () => {
          irParaEtapa(i.etapa, { focar: false });
          const alvo = i.campo ? focoDoCampo(i.campo) : null;
          if (alvo) alvo.focus(); else area.querySelector(`#titulo-etapa-${i.etapa}`).focus();
        } }, `Ver na etapa ${i.etapa}`)))));
  }

  async function salvar() {
    if (estado.salvando || !sujo()) return;
    estado.errosDoServidor = [];
    estado.erros = conferirRascunho(estado.rascunho, estado.opcoes);
    mostrarErros();
    desenharResumoDeErros();
    atualizarEtapas();
    atualizarBarra();
    if (estado.erros.length) {
      irParaEtapa(etapaDoCampo(estado.erros[0].campo), { focar: false });
      anunciar('O perfil não foi salvo. Corrija os pontos indicados.');
      ref.erros.focus();
      ref.erros.scrollIntoView({ block: 'center' });
      return;
    }
    estado.salvando = true;
    atualizarBarra();
    try {
      const gravado = await escrever('PUT', '/api/perfil', perfilParaSalvar(estado.rascunho, estado.opcoes, estado.original));
      estado.original = rascunhoDoPerfil(gravado.perfil);
      estado.rascunho = copiar(estado.original);
      estado.errosDoPerfil = [];
      estado.avisosDoPerfil = gravado.avisos || [];
      pendente = null;
      let texto = 'Tudo salvo.';
      try {
        texto = 'Tudo salvo. ' + resumoDaReavaliacao(await escrever('POST', '/api/leads/reavaliar')).replace(/^Perfil salvo\.\s*/, '');
      } catch (erro) {
        if (!(erro instanceof ErroApi)) throw erro;
        texto = 'O perfil foi salvo, mas não consegui dar nota de novo aos leads: ' + erro.message + ' Salve de novo para tentar.';
      }
      ultimoResultado = { texto, ate: Date.now() + DURACAO_DO_TUDO_SALVO_MS };
      estado.salvando = false;
      desenhar();  // volta a mostrar o que o servidor guardou, que pode ter ajustes
      anunciar(texto);
      if (ctx.atualizarEstado) ctx.atualizarEstado();
      if (ctx.recarregarContagem) ctx.recarregarContagem();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      estado.salvando = false;
      estado.errosDoServidor = erro.erros && erro.erros.length ? erro.erros : [erro.message];
      desenharResumoDeErros();
      atualizarEtapas();
      atualizarBarra();
      barra.no.classList.remove('recolhida');
      anunciar('O perfil não foi salvo.');
      ref.erros.focus();
      ref.erros.scrollIntoView({ block: 'center' });
    }
  }

  // ---------- tela

  function desenhar() {
    ref.ouvintes = [];
    limpar(area);
    if (estado.carregando) { area.append(blocoCarregando('Carregando o seu perfil...')); barra.no.hidden = true; return; }
    if (estado.erro) {
      barra.no.hidden = true;
      area.append(blocoEstado({
        tipo: 'bad', selo: '!', titulo: 'Não consegui abrir o seu perfil', texto: estado.erro.message,
        acoes: [{ rotulo: 'Tentar de novo', primario: true, aoClicar: carregar }],
      }));
      return;
    }
    ref.erros = el('div', { class: 'aviso-inline erros-perfil', role: 'alert', tabindex: '-1', hidden: true });
    ref.avisosDoPerfil = estado.errosDoPerfil.length || estado.avisosDoPerfil.length
      ? el('div', { class: 'aviso-inline', role: 'note' },
        el('b', {}, estado.errosDoPerfil.length ? 'O perfil que está salvo tem problemas:' : 'O painel ajustou alguns pontos do perfil salvo:'),
        el('ul', { class: 'lista-erros' }, [...estado.errosDoPerfil, ...estado.avisosDoPerfil].map((m) => el('li', {}, m))),
        el('p', {}, 'Corrija abaixo e salve.'))
      : null;
    barra.descartar.onclick = () => {
      estado.rascunho = copiar(estado.original);
      estado.erros = [];
      estado.errosDoServidor = [];
      pendente = null;
      desenhar();
      anunciar('As mudanças foram descartadas.');
    };
    ref.voltar = el('button', { class: 'btn', type: 'button', onClick: () => irParaEtapa(estado.etapa - 1) }, 'Voltar');
    ref.continuar = el('button', { class: 'btn btn-primary', type: 'button', onClick: () => irParaEtapa(estado.etapa + 1) }, 'Continuar');
    ref.salvarFim = el('button', { class: 'btn btn-primary', type: 'submit', form: 'form-oferta' }, 'Salvar e dar nota de novo');
    const formulario = el('form', { class: 'form-oferta', id: 'form-oferta', novalidate: true,
      onSubmit: (evento) => { evento.preventDefault(); salvar(); },
      // Enter em um campo de texto não salva sem querer
      onKeydown: (evento) => { if (evento.key === 'Enter' && evento.target.tagName === 'INPUT' && evento.target.type === 'text') evento.preventDefault(); } },
      ref.avisosDoPerfil, ref.erros, nav(),
      etapa1(), etapa2(), etapa3(), etapa4(), etapa5(),
      el('div', { class: 'rodape-etapa' }, ref.voltar, el('span', { class: 'espaco' }), ref.continuar, ref.salvarFim),
      el('p', { class: 'hint' }, TEXTO_SEM_IA));
    ref.ouvintes.push(atualizarBarra);
    area.append(formulario);
    mostrarErros();
    desenharResumoDeErros();
    atualizarEtapas();
    atualizarBarra();
    mostrarTudoSalvo();
  }

  raiz.append(barra.no);
  carregar();

  return () => {
    vivo = false;
    clearTimeout(temporizadorDoSalvo);
    window.removeEventListener('beforeunload', avisoDeSaida);
    window.removeEventListener('scroll', aoRolar);
    barra.no.remove();
    guardar();
  };
}
