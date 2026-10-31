// Tela Leads: tabela, filtros, carregamento por partes, gaveta com a mensagem, status e exportação.
//
// Os dados dos leads vêm do Google Maps e NÃO são confiáveis. Tudo entra na página como texto
// (el() usa nós de texto) e links só são criados depois de validados (urlSegura, linkWhatsApp).
// O painel não gera texto por IA e não tem envio em massa: a mensagem vem pronta do servidor
// (modelos), a pessoa revisa e abre o WhatsApp de um lead por vez.
import { ler, escrever, baixar, seguidor, ABANDONADA, ErroApi } from './api.js';
import { el, limpar, blocoEstado, blocoCarregando, copiarTexto, avisar } from './dom.js';
import {
  PAGINA_LEADS, STATUS_DO_LEAD, FILTROS_PADRAO, rotuloDoStatus, formatarNota, tipoDeSite, linkWhatsApp,
  avisoDeConformidade, filtrosAtivos, situacaoDaLista, resumoDaLista, quantosFaltam, urlSegura, plural,
} from './util.js';

const LETRAS = ['A', 'B', 'C'];

// ---------- peças de desenho (exportadas para os testes)

export function etiquetaDoSite(site) {
  const tipo = tipoDeSite(site);
  if (tipo === 'nenhum') return el('span', { class: 'tag good', title: 'O Google Maps não mostra site para este negócio' }, 'Não tem');
  if (tipo === 'rede') return el('span', { class: 'tag warn', title: 'O site cadastrado é só uma rede social' }, 'Só rede social');
  return el('span', { class: 'tag neutral' }, 'Tem site');
}

export function etiquetaDoTelefone(lead) {
  if (!lead.telefone) return el('span', { class: 'tag neutral' }, 'Sem telefone');
  if (lead.celular) {
    return el('span', { class: 'tag good', title: 'Estimativa pelo número: o Google não diz se é WhatsApp' }, 'Celular');
  }
  return el('span', { class: 'tag neutral' }, 'Fixo');
}

function letraSegura(letra) {
  return LETRAS.includes(letra) ? letra : 'C';
}

export function selo(lead) {
  if (lead.excluido_por) return el('span', { class: 'tag neutral', title: lead.excluido_por }, 'Fora da lista');
  return el('span', { class: 'q ' + letraSegura(lead.letra), title: `Qualidade ${lead.letra}` }, letraSegura(lead.letra));
}

export function textoDoPorQue(lead) {
  if (lead.excluido_por) return 'Motivo: ' + lead.excluido_por;
  return (lead.por_que_curto || []).join(', ') || 'Nenhuma regra do seu perfil bateu';
}

export function criarLinha(lead, aoAbrir) {
  const abrir = () => aoAbrir(lead.id, linha);
  const linha = el('tr', {
    tabindex: 0, class: lead.excluido_por ? 'excluido' : null, dataset: { id: lead.id },
    onClick: abrir,
    onKeydown: (evento) => {
      if (evento.key === 'Enter' || evento.key === ' ') { evento.preventDefault(); abrir(); }
    },
  },
  el('td', { class: 'name' }, el('b', {}, lead.nome),
    el('small', {}, [lead.categoria, lead.telefone].filter(Boolean).join(' · '),
      el('span', { class: 'so-celular' }, ` · Nota ${formatarNota(lead.nota_maps)} (${lead.avaliacoes ?? 0})`))),
  el('td', { class: 'num col-nota' }, `${formatarNota(lead.nota_maps)} (${lead.avaliacoes ?? 0})`),
  el('td', { class: 'col-site' }, etiquetaDoSite(lead.site)),
  el('td', { class: 'col-zap' }, etiquetaDoTelefone(lead)),
  el('td', {}, selo(lead)),
  el('td', { class: 'porque col-porque', title: (lead.motivos || []).join('; ') }, textoDoPorQue(lead)),
  el('td', { class: 'status-cel', dataset: { status: lead.status } }, rotuloDoStatus(lead.status)));
  return linha;
}

export function blocoPorQue(detalhe) {
  if (detalhe.excluido_por) {
    return el('div', { class: 'sect' }, el('h3', {}, 'Por que está fora da lista'),
      el('p', {}, detalhe.excluido_por.charAt(0).toUpperCase() + detalhe.excluido_por.slice(1)
        + '. Ele só aparece com o filtro "Só os excluídos" ou "Todos".'));
  }
  const itens = detalhe.por_que || [];
  if (!itens.length) {
    return el('div', { class: 'sect' }, el('h3', {}, 'Por que essa nota'),
      el('ul', { class: 'why vazio' }, el('li', {}, 'Nenhuma regra do seu perfil bateu com este negócio.')));
  }
  return el('div', { class: 'sect' }, el('h3', {}, 'Por que essa nota'),
    el('ul', { class: 'why' }, itens.map((i) =>
      el('li', {}, el('span', {}, i.texto, el('small', {}, `+${i.pontos} ${plural(i.pontos, 'ponto', 'pontos')}`))))));
}

function linhaDeContato(rotulo, ...conteudo) {
  return [el('dt', {}, rotulo), el('dd', {}, conteudo)];
}

export function blocoContato(d) {
  const site = urlSegura(d.site);
  const mapa = urlSegura(d.link);
  const abrir = (url, texto) => el('a', { href: url, target: '_blank', rel: 'noopener noreferrer' }, texto);
  return el('div', { class: 'sect' }, el('h3', {}, 'Contato'),
    el('dl', { class: 'contato' },
      linhaDeContato('Telefone', d.telefone || 'Não informado'),
      linhaDeContato('Site', d.site ? (site ? abrir(site, d.site) : d.site) : 'Não tem'),
      d.emails && d.emails.length ? linhaDeContato('E-mails', d.emails.join(', ')) : null,
      linhaDeContato('Endereço', d.endereco || 'Não informado'),
      mapa ? linhaDeContato('Mapa', abrir(mapa, 'Ver no Google Maps')) : null));
}

// Texto do aviso de conformidade. Afirma só fatos (o que a pessoa respondeu e o que o kit faz e não faz)
// e não promete proteção nem cumprimento de regra nenhuma.
export const TEXTOS_CONFORMIDADE = {
  regulado: 'Você informou que a sua área tem regras de publicidade ou de abordagem.',
  incerto: 'Você respondeu que não sabe se a sua área tem regras de publicidade ou de abordagem.',
  orientacaoRegulado: 'Veja as regras do seu conselho ou órgão de classe antes de enviar qualquer mensagem.',
  orientacaoIncerto: 'Vale descobrir isso antes de enviar mensagens.',
  limites: 'O kit não confere se uma mensagem cumpre essas regras. Os textos do kit são modelos, e enviar ou não é sempre decisão sua. Isto não é aconselhamento jurídico.',
};

export function blocoConformidade(aviso, pequeno) {
  if (!aviso) return null;
  const regulado = aviso.tipo === 'regulado';
  return el('section', { class: 'conformidade' + (pequeno ? ' pequeno' : ''), role: 'note', 'aria-label': 'Aviso de conformidade' },
    el('div', { class: 'selo-mini', 'aria-hidden': 'true' }, '!'),
    el('div', {},
      el('p', {}, el('b', {}, regulado ? TEXTOS_CONFORMIDADE.regulado : TEXTOS_CONFORMIDADE.incerto),
        regulado && aviso.detalhe ? ` Resposta: ${aviso.detalhe}.` : '',
        ' ', regulado ? TEXTOS_CONFORMIDADE.orientacaoRegulado : TEXTOS_CONFORMIDADE.orientacaoIncerto),
      pequeno ? null : el('p', {}, TEXTOS_CONFORMIDADE.limites)));
}

function salvarArquivo(blob, nome) {
  const url = URL.createObjectURL(blob);
  const ancora = el('a', { href: url, download: nome });
  document.body.append(ancora);
  ancora.click();
  ancora.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

function opcao(valor, texto, atual) {
  return el('option', { value: valor, selected: String(valor) === String(atual) }, texto);
}

// ---------- gaveta do lead

function criarGaveta({ perfil, aoMudarStatus }) {
  let aberta = null;      // { id, origem }
  let fundo = null;
  let painel = null;
  let sequencia = 0;
  const pendentes = new Set();  // salvamentos adiados que ainda precisam ser enviados ao fechar

  const aoTecla = (evento) => {
    if (!painel) return;
    if (evento.key === 'Escape') { evento.preventDefault(); fechar(); return; }
    if (evento.key !== 'Tab') return;
    const foco = [...painel.querySelectorAll('button, a[href], select, textarea, input')].filter((n) => !n.disabled);
    if (!foco.length) return;
    const primeiro = foco[0];
    const ultimo = foco[foco.length - 1];
    if (evento.shiftKey && document.activeElement === primeiro) { evento.preventDefault(); ultimo.focus(); }
    else if (!evento.shiftKey && document.activeElement === ultimo) { evento.preventDefault(); primeiro.focus(); }
  };

  function fechar() {
    if (!painel) return;
    for (const enviar of [...pendentes]) enviar();
    const origem = aberta && aberta.origem;
    document.removeEventListener('keydown', aoTecla);
    fundo.remove();
    painel.remove();
    fundo = painel = aberta = null;
    sequencia += 1;
    if (origem && origem.isConnected) origem.focus();
  }

  async function abrir(id, origem) {
    if (painel) fechar();
    const minha = ++sequencia;
    aberta = { id, origem };
    fundo = el('div', { class: 'scrim', onClick: fechar });
    painel = el('aside', { class: 'drawer', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Detalhes do lead' });
    document.body.append(fundo, painel);
    document.addEventListener('keydown', aoTecla);
    await carregar(id, minha);
  }

  async function carregar(id, minha) {
    limpar(painel);
    painel.append(botaoFechar(), blocoCarregando('Abrindo o lead...'));
    let detalhe;
    try {
      detalhe = await ler(`/api/leads/${id}`);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (minha !== sequencia) return;
      limpar(painel);
      painel.append(botaoFechar(), blocoEstado({
        tipo: 'bad', selo: '!', titulo: 'Não consegui abrir este lead', texto: erro.message,
        acoes: [{ rotulo: 'Tentar de novo', primario: true, aoClicar: () => carregar(id, minha) }],
      }));
      painel.querySelector('.x').focus();
      return;
    }
    if (minha !== sequencia) return;  // outro lead foi aberto, ou a gaveta fechou
    desenhar(detalhe);
  }

  function botaoFechar() {
    return el('div', { class: 'dr-head' }, el('span', {}), el('button', { class: 'x', type: 'button', 'aria-label': 'Fechar', onClick: fechar }, '×'));
  }

  function desenhar(d) {
    limpar(painel);
    const canais = Object.keys(d.mensagens || {});
    let canal = canais.includes('whatsapp') ? 'whatsapp' : canais[0];
    let editada = d.mensagem_editada || '';
    const modelo = () => (canal && d.mensagens[canal] ? d.mensagens[canal].texto : '');

    const erroInline = el('div', { class: 'aviso-inline', role: 'alert', hidden: true });
    const mostrarErro = (texto) => { erroInline.textContent = texto; erroInline.hidden = !texto; };

    // ---- cabeçalho e etiquetas
    const cabecalho = el('div', { class: 'dr-head' },
      el('div', {}, el('h2', {}, d.nome), el('p', {}, [d.categoria, d.endereco].filter(Boolean).join(' · '))),
      el('button', { class: 'x', type: 'button', 'aria-label': 'Fechar', onClick: fechar }, '×'));
    const etiquetas = el('div', { class: 'dr-tags' }, selo(d), etiquetaDoSite(d.site), etiquetaDoTelefone(d),
      el('span', { class: 'tag neutral' }, `Nota ${formatarNota(d.nota_maps)} (${d.avaliacoes ?? 0})`),
      el('span', { class: 'tag neutral' }, `${d.nota} ${plural(d.nota, 'ponto', 'pontos')}`));

    // ---- mensagem
    const area = el('textarea', { class: 'msg', id: 'gaveta-mensagem', 'aria-label': 'Mensagem para enviar', spellcheck: 'true' });
    area.value = editada || modelo();
    const indicadorMsg = el('div', { class: 'salvo', role: 'status' });
    const notaDaMensagem = el('p', { class: 'note' });
    const seletorCanal = canais.length > 1
      ? el('select', { class: 'select', 'aria-label': 'Canal da mensagem', onChange: (e) => {
        canal = e.target.value;
        if (!editada) area.value = modelo();
        atualizarMensagem();
      } }, canais.map((c) => el('option', { value: c, selected: c === canal }, c === 'whatsapp' ? 'WhatsApp' : c === 'email' ? 'E-mail' : c)))
      : null;
    const voltar = el('button', { class: 'btn btn-small', type: 'button', onClick: () => {
      editada = '';
      area.value = modelo();
      atualizarMensagem();
      guardar('mensagem_editada', '', indicadorMsg);
    } }, 'Voltar ao modelo');

    const zap = el('a', { class: 'btn', target: '_blank', rel: 'noopener noreferrer' }, 'Abrir no WhatsApp');
    const copiar = el('button', { class: 'btn btn-primary', type: 'button', onClick: async () => {
      avisar((await copiarTexto(area.value)) ? 'Mensagem copiada.' : 'Não consegui copiar. Selecione o texto e use Ctrl+C.');
    } }, 'Copiar mensagem');
    const notaZap = el('p', { class: 'note' });

    function atualizarMensagem() {
      if (seletorCanal) seletorCanal.hidden = !!editada;
      voltar.hidden = !editada;
      notaDaMensagem.textContent = !canais.length
        ? 'O seu perfil não tem modelo de mensagem para os canais escolhidos. Escreva a sua aqui.'
        : editada
          ? 'Você editou esta mensagem. A edição vale para todos os canais e fica salva só neste lead.'
          : (d.mensagens[canal] && d.mensagens[canal].padrao)
            ? 'Esta é a mensagem padrão do kit. Edite à vontade: a edição fica salva só neste lead.'
            : 'Mensagem pronta do seu perfil. Edite à vontade: a edição fica salva só neste lead.';
      const link = canal === 'whatsapp' || !canais.length ? linkWhatsApp(d.whatsapp_numero, area.value) : null;
      if (link) {
        zap.setAttribute('href', link.url);
        zap.removeAttribute('aria-disabled');
        notaZap.textContent = link.comMensagem
          ? 'O envio é sempre manual: o WhatsApp abre com a mensagem pronta e você aperta enviar. Um lead por vez.'
          : 'A mensagem é grande demais para ir no link. O WhatsApp abre sem texto: copie e cole a mensagem.';
      } else {
        zap.removeAttribute('href');
        zap.setAttribute('aria-disabled', 'true');
        notaZap.textContent = !d.whatsapp_numero
          ? 'O número não parece ser de celular, então não há link do WhatsApp. Você pode ligar ou usar outro canal.'
          : 'Escolha o canal WhatsApp para abrir a conversa.';
      }
    }

    let temporizador = null;
    const enviarMensagem = () => {
      clearTimeout(temporizador);
      temporizador = null;
      pendentes.delete(enviarMensagem);
      const igual = area.value.trim() === modelo().trim();
      editada = igual ? '' : area.value;
      atualizarMensagem();
      return guardar('mensagem_editada', editada, indicadorMsg);
    };
    area.addEventListener('input', () => {
      indicadorMsg.dataset.estado = '';
      indicadorMsg.textContent = 'Editando...';
      const link = canal === 'whatsapp' || !canais.length ? linkWhatsApp(d.whatsapp_numero, area.value) : null;
      if (link) zap.setAttribute('href', link.url);
      clearTimeout(temporizador);
      pendentes.add(enviarMensagem);
      temporizador = setTimeout(enviarMensagem, 800);
    });
    area.addEventListener('blur', () => { if (pendentes.has(enviarMensagem)) enviarMensagem(); });
    atualizarMensagem();

    // ---- status e anotação
    const indicadorStatus = el('div', { class: 'salvo', role: 'status' });
    const seletorStatus = el('select', { class: 'select', id: 'gaveta-status' },
      STATUS_DO_LEAD.map((s) => opcao(s, rotuloDoStatus(s), d.status)));
    seletorStatus.addEventListener('change', async () => {
      const novo = seletorStatus.value;
      const anterior = d.status;
      seletorStatus.disabled = true;
      mostrarErro('');
      indicadorStatus.textContent = 'Salvando...';
      try {
        await escrever('PATCH', `/api/leads/${d.id}`, { status: novo });
        d.status = novo;
        indicadorStatus.dataset.estado = '';
        indicadorStatus.textContent = 'Salvo.';
        aoMudarStatus(d.id, novo);
      } catch (erro) {
        if (!(erro instanceof ErroApi)) throw erro;
        seletorStatus.value = anterior;  // nada mudou: volta ao que estava
        indicadorStatus.textContent = '';
        mostrarErro(`Não consegui marcar o status. ${erro.message} O status continua "${rotuloDoStatus(anterior)}".`);
        avisar('Não consegui marcar o status. Nada foi alterado.');
      } finally {
        seletorStatus.disabled = false;
      }
    });

    const indicadorNota = el('div', { class: 'salvo', role: 'status' });
    const areaNota = el('textarea', { class: 'nota', id: 'gaveta-anotacao', 'aria-label': 'Anotação sobre o lead', maxlength: '2000' });
    areaNota.value = d.anotacao || '';
    let temporizadorNota = null;
    const enviarNota = async () => {
      clearTimeout(temporizadorNota);
      temporizadorNota = null;
      pendentes.delete(enviarNota);
      await guardar('anotacao', areaNota.value, indicadorNota);
    };
    areaNota.addEventListener('input', () => {
      indicadorNota.dataset.estado = '';
      indicadorNota.textContent = 'Editando...';
      clearTimeout(temporizadorNota);
      pendentes.add(enviarNota);
      temporizadorNota = setTimeout(enviarNota, 800);
    });
    areaNota.addEventListener('blur', () => { if (pendentes.has(enviarNota)) enviarNota(); });

    async function guardar(campo, valor, indicador) {
      indicador.dataset.estado = '';
      indicador.textContent = 'Salvando...';
      try {
        await escrever('PATCH', `/api/leads/${d.id}`, { [campo]: valor });
        indicador.textContent = 'Salvo.';
        return true;
      } catch (erro) {
        if (!(erro instanceof ErroApi)) throw erro;
        indicador.dataset.estado = 'erro';
        indicador.textContent = 'Não salvou. Sua edição continua na tela.';
        mostrarErro(`Não consegui salvar. ${erro.message}`);
        avisar('Não consegui salvar. Sua edição continua na tela.');
        return false;
      }
    }

    painel.append(
      cabecalho, etiquetas, erroInline, blocoPorQue(d),
      el('div', { class: 'sect' },
        el('h3', {}, 'Mensagem sugerida'),
        el('div', { class: 'field' },
          blocoConformidade(perfil.aviso, true),
          seletorCanal,
          area, indicadorMsg, notaDaMensagem, voltar)),
      el('div', { class: 'actions' }, copiar, zap),
      notaZap,
      el('div', { class: 'sect' }, el('h3', {}, 'Acompanhamento'),
        el('div', { class: 'field' },
          el('label', { class: 'label', for: 'gaveta-status' }, 'Status do lead'), seletorStatus, indicadorStatus,
          el('label', { class: 'label', for: 'gaveta-anotacao' }, 'Anotação'), areaNota, indicadorNota)),
      blocoContato(d),
      el('p', { class: 'note' }, 'Revise antes de enviar e mande uma mensagem por vez, só para quem faz sentido contatar.'));
    painel.querySelector('.x').focus();
  }

  return { abrir, fechar, aberta: () => aberta };
}

// ---------- a tela

export function montarLeads(raiz, ctx) {
  const estado = {
    filtros: { ...FILTROS_PADRAO }, leads: [], total: 0, contagem: { A: 0, B: 0, C: 0 },
    carregando: true, carregandoMais: false, erro: null, perfil: { aviso: null }, buscas: [],
  };
  const recado = ctx.consumirParametros ? ctx.consumirParametros() : null;
  if (recado && recado.busca) estado.filtros.busca = String(recado.busca);  // veio de "Ver os leads desta busca"
  const seguirLista = seguidor();
  let temporizadorBusca = null;
  let vivo = true;
  let exportando = false;

  const subtitulo = el('p', {});
  const conformidade = el('div', {});
  const pilulas = el('div', { class: 'filters', role: 'group', 'aria-label': 'Filtrar pela nota' });
  const campoTexto = el('input', { class: 'input', type: 'search', id: 'filtro-texto', placeholder: 'Nome, categoria, endereço ou telefone', autocomplete: 'off' });
  const seletorStatus = el('select', { class: 'select', id: 'filtro-status' });
  const seletorExcluidos = el('select', { class: 'select', id: 'filtro-excluidos' });
  const seletorBusca = el('select', { class: 'select', id: 'filtro-busca' });
  const limparFiltros = el('button', { class: 'btn btn-small', type: 'button', hidden: true, onClick: () => {
    estado.filtros = { ...FILTROS_PADRAO };
    campoTexto.value = '';
    sincronizarFiltros();
    carregar(true);
  } }, 'Limpar filtros');
  const botaoXlsx = el('button', { class: 'btn btn-primary', type: 'button', onClick: () => exportar('xlsx', botaoXlsx) }, 'Baixar planilha (.xlsx)');
  const botaoCsv = el('button', { class: 'btn', type: 'button', onClick: () => exportar('csv', botaoCsv) }, 'Baixar CSV');
  const erroExportar = el('div', { class: 'aviso-inline', role: 'alert', hidden: true });
  const area = el('div', {});
  const legenda = el('p', { class: 'legend' },
    'Como a nota é calculada: o painel soma pontos das regras do seu perfil (por exemplo, não ter site ou ter nota alta no Google). ',
    'Clique em um lead para ver o motivo. O Google Maps não diz se o número é WhatsApp: o painel marca como celular os números com 9 dígitos, ',
    'e mesmo assim vale confirmar antes de contar com ele.');

  raiz.append(
    el('div', { class: 'page-head' }, el('h1', {}, 'Leads'), subtitulo),
    conformidade,
    el('div', { class: 'toolbar' },
      el('div', { class: 'toolbar-linha' }, pilulas,
        el('div', { class: 'actions' }, limparFiltros, botaoXlsx, botaoCsv)),
      el('div', { class: 'filtros-extra' },
        el('label', { for: 'filtro-texto' }, 'Buscar', campoTexto),
        el('label', { for: 'filtro-status' }, 'Status', seletorStatus),
        el('label', { for: 'filtro-excluidos' }, 'Lista', seletorExcluidos),
        el('label', { for: 'filtro-busca' }, 'Busca', seletorBusca))),
    erroExportar, area, legenda);
  const barra = raiz.querySelector('.toolbar');

  const gaveta = criarGaveta({
    perfil: estado.perfil,
    aoMudarStatus: (id, status) => {
      const lead = estado.leads.find((l) => l.id === id);
      if (!lead) return;
      lead.status = status;
      if (estado.filtros.status && estado.filtros.status !== status) {  // saiu do filtro de status
        estado.leads = estado.leads.filter((l) => l.id !== id);
        estado.total = Math.max(0, estado.total - 1);
      }
      desenharLista();
    },
  });

  // ---- filtros
  function paramsDeFiltro() {
    const f = estado.filtros;
    return { letra: f.letra, status: f.status, q: f.q, excluidos: f.excluidos, busca: f.busca, sem_site: f.sem_site, celular: f.celular };
  }

  function sincronizarFiltros() {
    const f = estado.filtros;
    limpar(seletorStatus).append(opcao('', 'Todos os status', f.status), ...STATUS_DO_LEAD.map((s) => opcao(s, rotuloDoStatus(s), f.status)));
    limpar(seletorExcluidos).append(
      opcao('nao', 'Só os da lista', f.excluidos), opcao('sim', 'Só os excluídos', f.excluidos), opcao('todos', 'Todos', f.excluidos));
    limpar(seletorBusca).append(opcao('', 'Todas as buscas', f.busca), ...estado.buscas.map((b) =>
      opcao(b.id, `#${b.id} ${b.categoria} em ${b.cidade}-${b.uf} (${b.total_leads ?? 0})`, f.busca)));
    limparFiltros.hidden = !filtrosAtivos(f).length;
    desenharPilulas();
  }

  function desenharPilulas() {
    const todos = estado.contagem.A + estado.contagem.B + estado.contagem.C;
    const itens = [['', 'Todos', todos], ...LETRAS.map((l) => [l, l, estado.contagem[l]])];
    const rapido = (chave, rotulo, dica) => el('button', {
      class: 'pill', type: 'button', title: dica, 'aria-pressed': String(estado.filtros[chave] === '1'), onClick: () => {
        estado.filtros[chave] = estado.filtros[chave] === '1' ? '' : '1';
        sincronizarFiltros();
        carregar(true);
      } }, rotulo);
    limpar(pilulas).append(...itens.map(([valor, rotulo, n]) =>
      el('button', { class: 'pill', type: 'button', 'aria-pressed': String(estado.filtros.letra === valor), onClick: () => {
        estado.filtros.letra = valor;
        sincronizarFiltros();
        carregar(true);
      } }, rotulo, el('em', {}, String(n)))),
    el('span', { class: 'sep', 'aria-hidden': 'true' }),
    rapido('sem_site', 'Sem site', 'Mesmo critério da nota: o Google Maps não mostra site para o negócio'),
    rapido('celular', 'Com celular', 'Mesmo critério da nota: telefone com DDD e 9 dígitos (estimativa, o Google não diz se é WhatsApp)'));
  }

  seletorStatus.addEventListener('change', () => { estado.filtros.status = seletorStatus.value; sincronizarFiltros(); carregar(true); });
  seletorExcluidos.addEventListener('change', () => { estado.filtros.excluidos = seletorExcluidos.value; sincronizarFiltros(); carregar(true); });
  seletorBusca.addEventListener('change', () => { estado.filtros.busca = seletorBusca.value; sincronizarFiltros(); carregar(true); });
  campoTexto.addEventListener('input', () => {
    estado.filtros.q = campoTexto.value.trim();
    clearTimeout(temporizadorBusca);
    temporizadorBusca = setTimeout(() => { sincronizarFiltros(); carregar(true); }, 300);
  });

  // ---- desenho da lista
  function atualizarBotoesDeExportar() {
    const semNada = estado.carregando || !!estado.erro || estado.total === 0;
    for (const botao of [botaoXlsx, botaoCsv]) {
      botao.disabled = semNada || exportando;
      botao.title = estado.total === 0 && !estado.carregando ? 'Não há leads na tela para baixar' : '';
    }
  }

  function desenharLista() {
    atualizarBotoesDeExportar();
    // Na primeira vez (nenhuma busca feita) só aparece o convite para buscar, sem filtros nem legenda.
    const primeiraVez = !estado.carregando && !estado.erro
      && situacaoDaLista({ total: estado.total, filtros: estado.filtros, buscasFeitas: estado.buscas.length > 0 }) === 'nenhuma-busca';
    barra.hidden = primeiraVez;
    legenda.hidden = primeiraVez;
    limpar(area);
    if (!estado.carregando && !estado.erro && !filtrosAtivos(estado.filtros).length) ctx.atualizarContagem(estado.total);
    const resumo = resumoDaLista(estado.leads.length, estado.total);
    subtitulo.textContent = estado.carregando ? 'Carregando...'
      : estado.total ? `${resumo}. Clique em um lead para ver o motivo da nota e a mensagem pronta.` : `${resumo}.`;

    if (estado.carregando) { area.append(blocoCarregando('Carregando os leads...')); return; }
    if (estado.erro) {
      area.append(blocoEstado({
        tipo: 'bad', selo: '!', titulo: 'Não consegui carregar os leads', texto: estado.erro.message,
        acoes: [{ rotulo: 'Tentar de novo', primario: true, aoClicar: () => carregar(true) }],
      }));
      return;
    }
    const situacao = situacaoDaLista({ total: estado.total, filtros: estado.filtros, buscasFeitas: estado.buscas.length > 0 });
    if (situacao === 'nenhuma-busca') {
      area.append(blocoEstado({
        selo: '0', titulo: 'Ainda não há leads',
        texto: 'Faça a primeira busca e os negócios aparecem aqui, já com nota e mensagem pronta.',
        acoes: [{ rotulo: 'Fazer uma busca', primario: true, aoClicar: () => ctx.irPara('buscar') }],
      }));
      return;
    }
    if (situacao === 'sem-leads-na-lista') {
      area.append(blocoEstado({
        selo: 'i', titulo: 'Todos os negócios ficaram fora da lista',
        texto: 'As buscas acharam negócios, mas as exclusões do seu perfil (por exemplo, sem telefone ou possível rede) tiraram todos da lista.',
        acoes: [{ rotulo: 'Ver os excluídos', primario: true, aoClicar: () => { estado.filtros.excluidos = 'todos'; sincronizarFiltros(); carregar(true); } }],
      }));
      return;
    }
    if (situacao === 'sem-resultado') {
      area.append(blocoEstado({
        selo: '?', titulo: 'Nenhum lead com esses filtros',
        texto: 'Tente tirar algum filtro ou mudar o que você digitou.',
        acoes: [{ rotulo: 'Limpar filtros', primario: true, aoClicar: () => limparFiltros.click() }],
      }));
      return;
    }
    const corpo = el('tbody', {}, estado.leads.map((l) => criarLinha(l, gaveta.abrir)));
    const faltam = quantosFaltam(estado.leads.length, estado.total, PAGINA_LEADS);
    const maisBotao = el('button', { class: 'btn', type: 'button', id: 'mostrar-mais', disabled: estado.carregandoMais, onClick: () => carregar(false) },
      estado.carregandoMais ? 'Carregando...' : `Mostrar mais ${faltam}`);
    area.append(el('div', { class: 'card' },
      el('div', { class: 'tablewrap' }, el('table', {},
        el('thead', {}, el('tr', {},
          el('th', {}, 'Negócio'), el('th', { class: 'col-nota' }, 'Nota no Google'), el('th', { class: 'col-site' }, 'Site'),
          el('th', { class: 'col-zap' }, 'Telefone'), el('th', {}, 'Qualidade'), el('th', { class: 'col-porque' }, 'Por quê'), el('th', {}, 'Status'))),
        corpo)),
      el('div', { class: 'rodape-lista' }, el('span', { role: 'status' }, resumoDaLista(estado.leads.length, estado.total)), faltam ? maisBotao : null)));
  }

  // ---- carga
  async function carregar(reiniciar) {
    if (reiniciar) { estado.carregando = true; estado.erro = null; } else { estado.carregandoMais = true; }
    desenharLista();
    const deslocamento = reiniciar ? 0 : estado.leads.length;
    const resultado = await seguirLista((sinal) => ler('/api/leads', { ...paramsDeFiltro(), limite: PAGINA_LEADS, offset: deslocamento }, sinal).then(
      (dados) => ({ dados }), (erro) => { if (erro instanceof ErroApi) return { erro }; throw erro; }));
    if (resultado === ABANDONADA || !vivo) return;
    estado.carregando = false;
    estado.carregandoMais = false;
    if (resultado.erro) {
      if (reiniciar) estado.erro = resultado.erro; else avisar('Não consegui carregar mais leads. ' + resultado.erro.message);
    } else {
      const { dados } = resultado;
      const vistos = new Set(reiniciar ? [] : estado.leads.map((l) => l.id));
      estado.leads = (reiniciar ? [] : estado.leads).concat(dados.leads.filter((l) => !vistos.has(l.id)));
      estado.total = dados.total;
      estado.contagem = dados.contagem_por_letra;
    }
    sincronizarFiltros();
    desenharLista();
  }

  async function carregarInicial() {
    try {
      const [perfil, buscas] = await Promise.all([ler('/api/perfil'), ler('/api/buscas')]);
      estado.perfil.aviso = avisoDeConformidade(perfil.perfil);
      estado.buscas = buscas.buscas;
      limpar(conformidade).append(blocoConformidade(estado.perfil.aviso, false) || '');
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      estado.carregando = false;
      estado.erro = erro;
      desenharLista();
      return;
    }
    sincronizarFiltros();
    await carregar(true);
  }

  // ---- exportação
  async function exportar(formato, botao) {
    exportando = true;
    atualizarBotoesDeExportar();
    erroExportar.hidden = true;
    try {
      const { blob, nome } = await baixar('/api/exportar', { formato, ...paramsDeFiltro() });
      const arquivo = nome === 'leads' ? `leads.${formato}` : nome;
      salvarArquivo(blob, arquivo);
      avisar(`Arquivo ${arquivo} baixado.`);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      erroExportar.textContent = `Não consegui baixar o arquivo. ${erro.message}`;
      erroExportar.hidden = false;
    } finally {
      exportando = false;
      atualizarBotoesDeExportar();
    }
  }

  sincronizarFiltros();
  desenharLista();
  carregarInicial();

  return () => {  // ao sair da aba
    vivo = false;
    clearTimeout(temporizadorBusca);
    gaveta.fechar();
  };
}
