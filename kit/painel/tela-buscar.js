// Tela Buscar: formulário, busca em andamento (com progresso real vindo do servidor), resumo ao fim,
// erros com mensagem própria e histórico.
//
// Regras desta tela:
// - Só uma busca por vez. Se já existe uma, a tela mostra ela, mesmo depois de recarregar a página,
//   porque o estado vem do servidor (/api/estado e /api/buscas/{id}), não da memória da página.
// - Não há botão de cancelar: nem o servidor nem o motor têm cancelamento. A tela diz isso.
// - O kit não promete quantidade de resultados. Resultado zero nunca aparece como sucesso.
// - Tudo que vem da busca (tipo de negócio, cidade, mensagens de erro) entra na página só como texto.
import { ler, escrever, ABANDONADA, ErroApi } from './api.js';
import { el, limpar, blocoEstado, blocoCarregando, cabecalhoDaTela, instrucoesComComando, avisar } from './dom.js';
import { motivoDoMotor } from './instrucoes.js';
import {
  ROTULOS_DE_TAMANHO, LIMITE_TEXTO_BUSCA, ETAPAS_DA_BUSCA, sugestoesDeCidade, sugestoesDeCategoria, validarBusca,
  formatarDuracao, quandoFoi, descreverBusca, indiceDaEtapa, percentualDaBusca, resumoDaBusca, plural,
} from './util.js';

export const TEXTO_RESULTADO_VARIA = 'Quantos negócios aparecem varia. O Google muda de uma busca para outra, e o resultado depende da cidade e do tipo de negócio. O kit não promete uma quantidade.';

export const TEXTO_PRIVACIDADE = {
  titulo: 'O que sai do seu computador',
  itens: [
    'O nome da cidade e o estado vão para o serviço de localização OpenStreetMap (Nominatim), que devolve as coordenadas. Esse serviço enxerga o seu endereço de internet, como qualquer site que você visita.',
    'O motor de busca roda no seu computador e consulta o Google Maps pela sua conexão, com o tipo de negócio, a cidade e essas coordenadas.',
    'Os leads, as notas, o seu perfil e as mensagens ficam só no seu computador.',
  ],
};

export const TEXTO_USO_RESPONSAVEL = {
  titulo: 'Uso responsável',
  texto: 'Pegar dados do Google Maps vai contra os termos de uso do Google. Telefone e e-mail são dados pessoais (LGPD). Fale com cada negócio com uma mensagem pessoal, um por vez, e pare quando pedirem. O envio é sempre manual.',
};

export const TEXTO_SEM_CANCELAR = 'Esta versão não tem como cancelar uma busca: ela termina sozinha. Você pode trocar de aba ou recarregar a página, e a busca continua no kit, desde que a janela do kit fique aberta. Só uma busca roda por vez.';

export const TEXTO_AVISO_IP = 'Buscas maiores fazem mais consultas seguidas ao Google. Se o Google notar muito uso, ele pode limitar o acesso da sua internet por um tempo.';

const CHAVE_AVISO_IP = 'lks-aviso-ip';
const INTERVALO_DA_BUSCA_MS = 2000;

function lerAvisoIp() {
  try { return localStorage.getItem(CHAVE_AVISO_IP) === '1'; } catch (erro) { return false; }
}

function gravarAvisoIp() {
  try { localStorage.setItem(CHAVE_AVISO_IP, '1'); } catch (erro) { /* sem armazenamento: vale só nesta visita */ }
}

// ---------- peças de desenho (exportadas para os testes)

// Cartão de progresso. É montado uma vez e atualizado no lugar a cada consulta ao servidor, para a barra
// não reiniciar a animação e para leitores de tela não reanunciarem o cartão inteiro.
export function criarProgresso(busca) {
  const titulo = el('h2', {});
  const tamanho = el('b', {});
  const tempo = el('b', {});
  const ponto = el('b', {});
  const blocoTempo = el('span', {}, 'Tempo decorrido: ', tempo);
  const blocoPonto = el('span', {}, 'Ponto: ', ponto);
  const estimativa = el('span', {});
  const preenchimento = el('i', {});
  const barra = el('div', { class: 'bar', role: 'progressbar', 'aria-label': 'Andamento da busca', 'aria-valuemin': '0', 'aria-valuemax': '100' }, preenchimento);
  const etapa = el('p', {});
  const passos = ETAPAS_DA_BUSCA.map((nome) => el('li', {}, nome));
  const semResposta = el('p', { class: 'aviso-inline', role: 'alert', hidden: true },
    'O kit não respondeu agora. Continuo tentando. Se o kit foi fechado, abra de novo.');
  const no = el('section', { class: 'card progress', dataset: { estado: 'andamento' } },
    titulo,
    el('div', { class: 'meta' }, el('span', {}, 'Tamanho: ', tamanho), blocoTempo, blocoPonto, estimativa),
    barra, etapa, el('ol', { class: 'steps' }, passos), semResposta,
    el('div', { class: 'notas' }, el('p', {}, TEXTO_SEM_CANCELAR)));

  function atualizar(b, { semResposta: sem = false } = {}) {
    const percentual = percentualDaBusca(b);
    const atual = indiceDaEtapa(b.etapa);
    titulo.textContent = `Buscando ${b.categoria} em ${b.cidade}-${b.uf}`;
    tamanho.textContent = ROTULOS_DE_TAMANHO[b.tamanho] || b.tamanho;
    blocoTempo.hidden = b.segundos === null || b.segundos === undefined;
    tempo.textContent = blocoTempo.hidden ? '' : formatarDuracao(b.segundos);
    blocoPonto.hidden = !(b.pontos > 1 && b.ponto > 0);
    ponto.textContent = blocoPonto.hidden ? '' : `${b.ponto} de ${b.pontos}`;
    estimativa.hidden = !b.tempo_estimado;
    estimativa.textContent = b.tempo_estimado ? `Estimativa: ${b.tempo_estimado} (pode variar)` : '';
    barra.classList.toggle('indeterminada', percentual === null);
    if (percentual === null) { barra.removeAttribute('aria-valuenow'); preenchimento.style.width = ''; }
    else { barra.setAttribute('aria-valuenow', String(percentual)); preenchimento.style.width = percentual + '%'; }
    etapa.textContent = b.etapa || 'Começando...';
    passos.forEach((li, i) => { li.className = i < atual ? 'feito' : (i === atual ? 'on' : ''); });
    semResposta.hidden = !sem;
  }

  atualizar(busca);
  return { no, atualizar };
}

export function criarResumo(busca, { aoVerLeads, aoVerTodos, aoOutra, aoRepetir }) {
  const r = resumoDaBusca(busca);
  const quando = busca.terminou_em || busca.criada_em;
  const botoes = [];
  if (r.temLeads) {
    botoes.push(el('button', { class: 'btn btn-primary', type: 'button', onClick: aoVerLeads }, 'Ver os leads desta busca'));
    botoes.push(el('button', { class: 'btn', type: 'button', onClick: aoVerTodos }, 'Ver todos os leads'));
  }
  if (r.tipo === 'erro' || r.tipo === 'parcial' || r.tipo === 'vazio') {
    botoes.push(el('button', { class: 'btn' + (r.temLeads ? '' : ' btn-primary'), type: 'button', onClick: aoRepetir },
      r.tipo === 'vazio' ? 'Mudar a busca' : 'Tentar de novo'));
  }
  if (r.tipo === 'sucesso') botoes.push(el('button', { class: 'btn', type: 'button', onClick: aoOutra }, 'Fazer outra busca'));
  return el('section', { class: 'card resultado', dataset: { tipo: r.tipo }, role: 'status' },
    el('h2', {}, r.titulo),
    el('div', { class: 'de-qual' }, [descreverBusca(busca), quando ? quandoFoi(quando) : '', ROTULOS_DE_TAMANHO[busca.tamanho]]
      .filter(Boolean).join(' · ')),
    r.texto ? el('p', {}, r.texto) : null,
    r.linhas.length ? el('ul', {}, r.linhas.map((l) => el('li', {}, l))) : null,
    r.tempo ? el('p', { class: 'hint' }, r.tempo) : null,
    r.dicas.length ? el('div', {}, el('h3', {}, 'O que você pode tentar'), el('ol', {}, r.dicas.map((d) => el('li', {}, d)))) : null,
    r.detalhe ? el('p', { class: 'detalhe' }, 'Mensagem do kit: ' + r.detalhe) : null,
    botoes.length ? el('div', { class: 'acoes' }, botoes) : null);
}

function textoDoStatus(busca) {
  if (busca.status === 'erro') return 'terminou com erro';
  if (busca.status !== 'ok') return 'em andamento';
  const total = busca.total_leads || 0;
  return total ? `${total} ${plural(total, 'negócio', 'negócios')}` : 'nenhum negócio';
}

export function criarHistorico(buscas, aoVer) {
  if (!buscas.length) return null;
  return el('section', { class: 'historico' },
    el('h2', {}, 'Buscas anteriores'),
    el('div', { class: 'card' }, el('ul', {}, buscas.map((b) =>
      el('li', { class: 'hist-linha' },
        el('div', {}, el('b', {}, descreverBusca(b)),
          el('small', {}, [ROTULOS_DE_TAMANHO[b.tamanho] || b.tamanho, quandoFoi(b.terminou_em || b.criada_em), textoDoStatus(b)]
            .filter(Boolean).join(' · '))),
        (b.total_leads || 0) > 0
          ? el('button', { class: 'btn btn-small', type: 'button', onClick: () => aoVer(b.id) }, 'Ver leads') : null)))));
}

export function criarBlocoDoMotor(diagnostico, aoVerificar) {
  const d = motivoDoMotor(diagnostico);
  return blocoEstado({
    tipo: 'warn', selo: '!', titulo: d.titulo, texto: d.texto,
    extras: instrucoesComComando({ passos: d.passos, comando: d.comando }),
    acoes: [{ rotulo: 'Verificar de novo', primario: true, aoClicar: aoVerificar }],
  });
}

// ---------- a tela

function esperar(ms) {
  return new Promise((resolver) => setTimeout(resolver, ms));
}

export function montarBuscar(raiz, ctx) {
  const estado = {
    opcoes: null, perfil: null, buscas: [], ativaId: null, ativa: null, semResposta: false,
    form: { categoria: '', cidade: '', uf: '', tamanho: 'rapida', email: false },
    enviando: false, erroEnvio: '', escondidoId: null, avisoIpVisto: lerAvisoIp(), carregando: true, erro: null,
  };
  let vivo = true;
  let geracao = 0;  // cada acompanhamento tem a sua; trocar de busca encerra o anterior
  const ref = {};
  let ultimoAnuncio = '';

  const anuncio = el('div', { class: 'so-leitor', role: 'status', 'aria-live': 'polite' });
  const areaMotor = el('div', {});
  const areaResumo = el('div', {});
  const areaProgresso = el('div', {});
  const areaFormulario = el('div', {});
  const areaHistorico = el('div', {});
  raiz.append(
    cabecalhoDaTela('Buscar leads', 'Escolha o tipo de negócio e a cidade. O painel busca no Google Maps e já dá nota a cada lead.'),
    anuncio, areaMotor, areaProgresso, areaResumo, areaFormulario, areaHistorico);

  // ---- estado do motor
  const motorNoAr = () => { const e = ctx.estado(); return !e || e.motor_no_ar !== false; };

  function desenharMotor() {
    limpar(areaMotor);
    const e = ctx.estado();
    if (e && e.motor_no_ar === false && !estado.ativaId) {
      areaMotor.append(criarBlocoDoMotor(e.motor_diagnostico, () => ctx.atualizarEstado()), el('div', { style: 'height:24px' }));
    }
    if (ref.botao) atualizarBotao();
  }

  // ---- formulário (construído uma vez, para não perder o que a pessoa digitou)
  function opcaoDeTamanho(t, marcado) {
    return [
      el('input', { type: 'radio', name: 'tamanho', id: 'tamanho-' + t.id, value: t.id, checked: marcado || null,
        onChange: () => { estado.form.tamanho = t.id; atualizarFormulario(); } }),
      el('label', { for: 'tamanho-' + t.id }, el('b', {}, ROTULOS_DE_TAMANHO[t.id] || t.id), el('span', {}, t.tempo_estimado)),
    ];
  }

  function construirFormulario() {
    const { opcoes, perfil } = estado;
    const cidades = sugestoesDeCidade(perfil, opcoes.ufs);
    const categorias = sugestoesDeCategoria(perfil);
    if (cidades.length && !estado.form.cidade) { estado.form.cidade = cidades[0].cidade; estado.form.uf = cidades[0].uf; }

    ref.categoria = el('input', { class: 'input', id: 'busca-categoria', type: 'text', maxlength: String(LIMITE_TEXTO_BUSCA),
      autocomplete: 'off', placeholder: 'Exemplo: padaria', 'aria-describedby': 'erro-categoria', value: estado.form.categoria });
    ref.cidade = el('input', { class: 'input', id: 'busca-cidade', type: 'text', maxlength: String(LIMITE_TEXTO_BUSCA),
      autocomplete: 'off', 'aria-describedby': 'erro-cidade', value: estado.form.cidade });
    ref.uf = el('select', { class: 'select', id: 'busca-uf', 'aria-describedby': 'erro-uf' },
      el('option', { value: '', selected: estado.form.uf === '' || null }, 'Escolha'),
      opcoes.ufs.map((u) => el('option', { value: u, selected: estado.form.uf === u || null }, u)));
    ref.erros = {
      categoria: el('p', { class: 'erro-campo', id: 'erro-categoria', role: 'alert', hidden: true }),
      cidade: el('p', { class: 'erro-campo', id: 'erro-cidade', role: 'alert', hidden: true }),
      uf: el('p', { class: 'erro-campo', id: 'erro-uf', role: 'alert', hidden: true }),
    };
    ref.email = el('input', { type: 'checkbox', id: 'busca-email', onChange: () => { estado.form.email = ref.email.checked; atualizarFormulario(); } });
    ref.avisoIp = el('div', { class: 'aviso-ip', role: 'note', hidden: true },
      el('p', {}, TEXTO_AVISO_IP),
      el('button', { class: 'btn btn-small', type: 'button', onClick: () => { estado.avisoIpVisto = true; gravarAvisoIp(); atualizarFormulario(); } }, 'Entendi'));
    ref.resumo = {
      busca: el('dd', {}), local: el('dd', {}), tamanho: el('dd', {}), extras: el('dd', {}),
    };
    ref.erroEnvio = el('div', { class: 'aviso-inline', role: 'alert', hidden: true });
    ref.botao = el('button', { class: 'btn btn-primary btn-block', id: 'botao-buscar', type: 'submit' }, 'Buscar leads');
    ref.nota = el('p', { class: 'estimativa' });
    ref.chipsCategoria = categorias.map((c) => el('button', { class: 'chip', type: 'button', onClick: () => {
      ref.categoria.value = c; estado.form.categoria = c; atualizarFormulario();
    } }, c));
    ref.chipsCidade = cidades.map((c) => el('button', { class: 'chip', type: 'button', onClick: () => {
      ref.cidade.value = c.cidade; ref.uf.value = c.uf; estado.form.cidade = c.cidade; estado.form.uf = c.uf; atualizarFormulario();
    } }, c.rotulo));

    ref.categoria.addEventListener('input', () => { estado.form.categoria = ref.categoria.value; atualizarFormulario(); });
    ref.cidade.addEventListener('input', () => { estado.form.cidade = ref.cidade.value; atualizarFormulario(); });
    ref.uf.addEventListener('change', () => { estado.form.uf = ref.uf.value; atualizarFormulario(); });

    const formulario = el('form', { class: 'form', novalidate: true, onSubmit: (evento) => { evento.preventDefault(); enviar(); } },
      el('div', { class: 'field' },
        el('label', { class: 'label', for: 'busca-categoria' }, 'Tipo de negócio'),
        ref.categoria, ref.erros.categoria,
        ref.chipsCategoria.length ? el('div', { class: 'chips', 'aria-label': 'Sugestões do seu perfil' }, ref.chipsCategoria) : null,
        el('p', { class: 'hint' }, ref.chipsCategoria.length ? 'As sugestões vêm do seu perfil. Você pode escrever qualquer outro tipo.' : 'Escreva como você procuraria no Google Maps.')),
      el('div', { class: 'field' },
        el('span', { class: 'label' }, 'Onde'),
        el('div', { class: 'row2' },
          el('div', {}, el('label', { class: 'hint', for: 'busca-uf' }, 'Estado'), ref.uf, ref.erros.uf),
          el('div', {}, el('label', { class: 'hint', for: 'busca-cidade' }, 'Cidade'), ref.cidade, ref.erros.cidade)),
        ref.chipsCidade.length ? el('div', { class: 'chips', 'aria-label': 'Regiões do seu perfil' }, ref.chipsCidade) : null,
        el('p', { class: 'hint' }, 'A busca cobre cerca de 10 km ao redor do centro da cidade.')),
      el('div', { class: 'field' },
        el('span', { class: 'label', id: 'rotulo-tamanho' }, 'Tamanho da busca'),
        el('div', { class: 'seg', role: 'radiogroup', 'aria-labelledby': 'rotulo-tamanho' },
          opcoes.tamanhos.map((t) => opcaoDeTamanho(t, estado.form.tamanho === t.id)),
          (opcoes.tamanhos_em_breve || []).map((id) => [
            el('input', { type: 'radio', name: 'tamanho', id: 'tamanho-' + id, value: id, disabled: true }),
            el('label', { for: 'tamanho-' + id }, el('b', {}, ROTULOS_DE_TAMANHO[id] || id), el('span', {}, 'em breve')),
          ])),
        el('p', { class: 'hint' }, 'Os tempos são estimativas e podem variar. ' + TEXTO_RESULTADO_VARIA),
        ref.avisoIp),
      el('div', { class: 'field' },
        el('span', { class: 'label' }, 'Contatos extras'),
        el('label', { class: 'check', for: 'busca-email' }, ref.email,
          el('div', {}, el('b', {}, 'Procurar e-mails nos sites'),
            el('span', {}, 'Deixa a busca bem mais lenta: em um teste nosso, levou cerca de 3 vezes mais. Só aparece e-mail que a empresa publicou no próprio site, e muitos negócios não publicam.')))));

    const lateral = el('aside', { class: 'card summary', 'aria-label': 'Resumo da busca' },
      el('h2', {}, 'Resumo'),
      el('dl', {},
        el('div', {}, el('dt', {}, 'Busca'), ref.resumo.busca),
        el('div', {}, el('dt', {}, 'Local'), ref.resumo.local),
        el('div', {}, el('dt', {}, 'Tamanho'), ref.resumo.tamanho),
        el('div', {}, el('dt', {}, 'Extras'), ref.resumo.extras)),
      ref.erroEnvio, ref.botao, ref.nota,
      el('div', { class: 'care' }, el('h3', {}, TEXTO_PRIVACIDADE.titulo),
        el('ul', {}, TEXTO_PRIVACIDADE.itens.map((i) => el('li', {}, i)))),
      el('div', { class: 'care' }, el('h3', {}, TEXTO_USO_RESPONSAVEL.titulo), el('p', {}, TEXTO_USO_RESPONSAVEL.texto)));

    // o botão de enviar fica na lateral, mas pertence ao formulário
    ref.botao.setAttribute('form', 'formulario-busca');
    formulario.id = 'formulario-busca';
    limpar(areaFormulario).append(el('div', { class: 'search-grid' }, el('div', { class: 'card' }, formulario), lateral));
    atualizarFormulario();
  }

  function atualizarFormulario() {
    const f = estado.form;
    const tamanho = estado.opcoes.tamanhos.find((t) => t.id === f.tamanho);
    ref.resumo.busca.textContent = f.categoria.trim() || 'sem tipo definido';
    ref.resumo.local.textContent = `${f.cidade.trim() || 'sem cidade'}${f.uf ? ', ' + f.uf : ''}`;
    ref.resumo.tamanho.textContent = `${ROTULOS_DE_TAMANHO[f.tamanho]}, ${tamanho.tempo_estimado}`;
    ref.resumo.extras.textContent = f.email ? 'E-mails nos sites' : 'Nenhum';
    ref.avisoIp.hidden = !(f.tamanho !== 'rapida' && !estado.avisoIpVisto);
    for (const chip of ref.chipsCategoria) chip.setAttribute('aria-pressed', String(chip.textContent.toLowerCase() === f.categoria.trim().toLowerCase()));
    for (const chip of ref.chipsCidade) chip.setAttribute('aria-pressed', String(chip.textContent === `${f.cidade.trim()}-${f.uf}`));
    atualizarBotao();
  }

  function atualizarBotao() {
    const f = estado.form;
    const tamanho = estado.opcoes && estado.opcoes.tamanhos.find((t) => t.id === f.tamanho);
    ref.botao.disabled = estado.enviando || !motorNoAr();
    ref.botao.textContent = estado.enviando ? 'Enviando...' : 'Buscar leads';
    ref.nota.textContent = !motorNoAr()
      ? 'Ligue o motor de busca para poder buscar. O aviso acima mostra como.'
      : (tamanho ? `Estimativa: ${tamanho.tempo_estimado}. Pode variar.` : '');
  }

  function mostrarErrosDeCampo(erros) {
    for (const campo of ['categoria', 'cidade', 'uf']) {
      const caixa = ref.erros[campo];
      caixa.textContent = erros[campo] || '';
      caixa.hidden = !erros[campo];
      const controle = ref[campo];
      if (erros[campo]) controle.setAttribute('aria-invalid', 'true'); else controle.removeAttribute('aria-invalid');
    }
    const primeiro = ['categoria', 'uf', 'cidade'].find((c) => erros[c]);
    if (primeiro) ref[primeiro].focus();
  }

  function mostrarErroDeEnvio(texto) {
    estado.erroEnvio = texto;
    ref.erroEnvio.textContent = texto;
    ref.erroEnvio.hidden = !texto;
  }

  async function enviar() {
    if (estado.enviando) return;
    const f = estado.form;
    const erros = validarBusca(f, estado.opcoes.ufs);
    mostrarErrosDeCampo(erros);
    mostrarErroDeEnvio('');
    if (Object.keys(erros).length) return;
    estado.enviando = true;
    atualizarBotao();
    try {
      const criada = await escrever('POST', '/api/buscas', {
        categoria: f.categoria.trim(), cidade: f.cidade.trim(), uf: f.uf, tamanho: f.tamanho, email: f.email,
      });
      await ctx.atualizarEstado();
      await acompanhar(criada.id);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (erro.tipo === 'conflito' && erro.extra && erro.extra.busca_em_andamento) {
        avisar('Já havia uma busca em andamento. Mostrando ela.');
        await ctx.atualizarEstado();
        await acompanhar(erro.extra.busca_em_andamento);
      } else {
        mostrarErroDeEnvio(erro.message);
        if (erro.tipo === 'ocupado') ctx.atualizarEstado();  // o motor caiu: atualiza o motivo na tela
      }
    } finally {
      estado.enviando = false;
      if (ref.botao) atualizarBotao();
    }
  }

  // ---- acompanhamento da busca em andamento (progresso real, vindo do servidor)
  async function acompanhar(id) {
    const minha = ++geracao;
    estado.ativaId = id;
    estado.ativa = null;
    estado.semResposta = false;
    estado.escondidoId = null;
    desenhar();
    while (vivo && minha === geracao) {
      const resultado = await ler(`/api/buscas/${id}`).then((busca) => ({ busca }), (erro) => {
        if (erro instanceof ErroApi) return { erro };
        throw erro;
      });
      if (!vivo || minha !== geracao) return;
      if (resultado.busca) {
        estado.semResposta = false;
        estado.ativa = resultado.busca;
        if (resultado.busca.status === 'ok' || resultado.busca.status === 'erro') { await terminar(id); return; }
        desenharProgresso();
      } else if (resultado.erro.tipo === 'naoencontrado') {
        await terminar(id);
        return;
      } else {
        estado.semResposta = true;  // kit fora do ar por um instante: continua tentando
        desenharProgresso();
      }
      await esperar(INTERVALO_DA_BUSCA_MS);
    }
  }

  async function terminar(id) {
    estado.ativaId = null;
    estado.ativa = null;
    await recarregarBuscas();
    ctx.atualizarEstado();
    if (ctx.recarregarContagem) ctx.recarregarContagem();
    const busca = estado.buscas.find((b) => b.id === id);
    if (busca) avisar(busca.status === 'ok' ? 'A busca terminou.' : 'A busca terminou com erro.');
    desenhar();
  }

  async function recarregarBuscas() {
    try {
      estado.buscas = (await ler('/api/buscas')).buscas;
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
    }
  }

  // ---- desenho geral
  function repetir(busca) {
    estado.form.categoria = busca.categoria;
    estado.form.cidade = busca.cidade;
    estado.form.uf = busca.uf;
    estado.form.tamanho = busca.tamanho in ROTULOS_DE_TAMANHO && estado.opcoes.tamanhos.some((t) => t.id === busca.tamanho) ? busca.tamanho : 'rapida';
    ref.categoria.value = estado.form.categoria;
    ref.cidade.value = estado.form.cidade;
    ref.uf.value = estado.form.uf;
    const radio = raiz.querySelector('#tamanho-' + estado.form.tamanho);
    if (radio) radio.checked = true;
    estado.escondidoId = busca.id;
    atualizarFormulario();
    desenhar();
    ref.categoria.focus();
  }

  function desenharProgresso() {
    if (!estado.ativaId) {
      limpar(areaProgresso);
      ref.progresso = null;
      ultimoAnuncio = '';
      return;
    }
    const busca = estado.ativa || { categoria: '...', cidade: '...', uf: '', tamanho: 'rapida', etapa: 'Começando...' };
    if (!ref.progresso) {
      ref.progresso = criarProgresso(busca);
      limpar(areaProgresso).append(ref.progresso.no, el('div', { style: 'height:24px' }));
    }
    ref.progresso.atualizar(busca, { semResposta: estado.semResposta });
    // Leitor de tela: só quando a etapa ou o ponto mudam, nunca a cada segundo do relógio.
    const fala = `${busca.etapa || 'Começando'}`;
    if (fala !== ultimoAnuncio) { ultimoAnuncio = fala; anuncio.textContent = fala; }
  }

  function desenhar() {
    if (!vivo) return;
    limpar(areaResumo);
    limpar(areaHistorico);
    desenharMotor();
    desenharProgresso();
    const andamento = !!estado.ativaId;
    areaFormulario.hidden = andamento || !estado.opcoes;
    if (andamento || !estado.opcoes) return;
    const terminadas = estado.buscas.filter((b) => b.status === 'ok' || b.status === 'erro');
    const ultima = terminadas[0];
    if (ultima && ultima.id !== estado.escondidoId) {
      areaResumo.append(criarResumo(ultima, {
        aoVerLeads: () => ctx.irPara('leads', { busca: ultima.id }),
        aoVerTodos: () => ctx.irPara('leads'),
        aoOutra: () => { estado.escondidoId = ultima.id; desenhar(); ref.categoria.focus(); },
        aoRepetir: () => repetir(ultima),
      }));
    }
    const historico = criarHistorico(terminadas.slice(ultima && ultima.id === estado.escondidoId ? 0 : 1, 6), (id) => ctx.irPara('leads', { busca: id }));
    if (historico) areaHistorico.append(historico);
  }

  // ---- inicio
  async function carregar() {
    estado.carregando = true;
    estado.erro = null;
    limpar(areaFormulario).append(blocoCarregando('Carregando...'));
    try {
      const [opcoes, perfil, buscas] = await Promise.all([ler('/api/opcoes'), ler('/api/perfil'), ler('/api/buscas')]);
      if (!vivo) return;
      estado.opcoes = opcoes;
      estado.perfil = perfil.perfil;
      estado.buscas = buscas.buscas;
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      estado.carregando = false;
      estado.erro = erro;
      limpar(areaFormulario).append(blocoEstado({
        tipo: 'bad', selo: '!', titulo: 'Não consegui abrir a tela de busca', texto: erro.message,
        acoes: [{ rotulo: 'Tentar de novo', primario: true, aoClicar: carregar }],
      }));
      return;
    }
    estado.carregando = false;
    construirFormulario();
    const andamento = (ctx.estado() || {}).busca_em_andamento;
    desenhar();
    if (andamento) acompanhar(andamento);
  }

  // uma busca pode ter sido iniciada por outra aba do navegador: a tela passa a mostrar ela
  const parar = ctx.observarEstado ? ctx.observarEstado(() => {
    if (!vivo || !estado.opcoes) return;
    desenharMotor();
    const andamento = (ctx.estado() || {}).busca_em_andamento;
    if (andamento && !estado.ativaId) acompanhar(andamento);
  }) : () => {};

  carregar();

  return () => {
    vivo = false;
    geracao += 1;
    parar();
  };
}
