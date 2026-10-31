// Botão "Ligar o motor": só aparece quando ajuda, nunca manda texto ao servidor e acompanha pelo estado.
import test from 'node:test';
import assert from 'node:assert/strict';
import { textoTodo, botoes } from './dom_falso.mjs';

const ligar = await import('../../kit/painel/ligar-motor.js');
const buscar = await import('../../kit/painel/tela-buscar.js');
const instrucoes = await import('../../kit/painel/instrucoes.js');

const diag = (estado) => ({ estado, titulo: 'T', texto: 'x', passos: ['Passo um.'], comando: estado === 'docker_ausente' ? null : 'docker compose up -d' });
const estadoDoKit = (extra = {}) => ({ motor_no_ar: false, motor_diagnostico: diag('motor_parado'), ligando_motor: null, ...extra });

function simularRede(status = 202, corpo = '{"estado":"ligando"}') {
  const chamadas = [];
  globalThis.document = globalThis.document || {};
  globalThis.document.querySelector = () => ({ content: 'tok-123' });
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push({ url, opcoes });
    return { ok: status < 400, status, text: async () => corpo };
  };
  return chamadas;
}

test('o botão só aparece com o Docker ligado e o motor desligado', () => {
  const faz = (estado) => ligar.criarLigarMotor({ estado, atualizarEstado: async () => estado, avisar: () => {} });
  assert.ok(faz(estadoDoKit()));
  assert.equal(faz(estadoDoKit({ motor_diagnostico: diag('docker_parado') })), null);
  assert.equal(faz(estadoDoKit({ motor_diagnostico: diag('docker_ausente') })), null);
  assert.equal(faz(estadoDoKit({ motor_no_ar: true, motor_diagnostico: null })), null);
  assert.equal(faz(estadoDoKit({ motor_diagnostico: null })), null);
  assert.equal(faz(null), null);
});

test('ligando: mostra "pode levar alguns minutos" e desativa o botão', () => {
  const estado = estadoDoKit({ ligando_motor: { estado: 'ligando', mensagem: ligar.TEXTO_LIGANDO } });
  const no = ligar.criarLigarMotor({ estado, atualizarEstado: async () => estado, avisar: () => {} });
  assert.match(textoTodo(no), /alguns minutos/);
  assert.ok('disabled' in botoes(no)[0].attributes);
});

test('erro do comando mostra a mensagem simples e deixa tentar de novo', () => {
  const estado = estadoDoKit({ ligando_motor: { estado: 'erro', mensagem: 'O Docker não conseguiu ligar o motor. Os detalhes ficaram salvos no arquivo dados/log-motor.txt.' } });
  const no = ligar.criarLigarMotor({ estado, atualizarEstado: async () => estado, avisar: () => {} });
  assert.match(textoTodo(no), /não conseguiu ligar o motor/);
  assert.ok(!('disabled' in botoes(no)[0].attributes));
});

test('o clique faz um POST sem corpo útil, com token, e depois acompanha o estado', async () => {
  const chamadas = simularRede();
  let verificacoes = 0;
  const estado = estadoDoKit();
  const no = ligar.criarLigarMotor({ estado, atualizarEstado: async () => { verificacoes += 1; return estadoDoKit({ motor_no_ar: true, motor_diagnostico: null }); }, avisar: () => {} });
  await botoes(no)[0].ouvintes.click[0]();
  assert.equal(chamadas.length, 1);
  assert.match(chamadas[0].url, /\/api\/motor\/ligar$/);
  assert.equal(chamadas[0].opcoes.method, 'POST');
  assert.equal(JSON.stringify(chamadas[0].opcoes.headers).includes('tok-123'), true);
  assert.deepEqual(JSON.parse(chamadas[0].opcoes.body || '{}'), {});  // nada digitado vai junto
  assert.equal(verificacoes, 1);
});

test('recusa do servidor vira aviso simples, sem quebrar', async () => {
  simularRede(409, '{"erro":"O motor já está ligado."}');
  const avisos = [];
  const estado = estadoDoKit();
  const no = ligar.criarLigarMotor({ estado, atualizarEstado: async () => estado, avisar: (t) => avisos.push(t) });
  await botoes(no)[0].ouvintes.click[0]();
  assert.deepEqual(avisos, ['O motor já está ligado.']);
});

test('chave do motor: igual quando nada mudou, diferente quando algo mudou', () => {
  assert.equal(ligar.chaveDoMotor(estadoDoKit()), ligar.chaveDoMotor(estadoDoKit()));
  assert.notEqual(ligar.chaveDoMotor(estadoDoKit()), ligar.chaveDoMotor(estadoDoKit({ ligando_motor: { estado: 'ligando', mensagem: 'x' } })));
  assert.notEqual(ligar.chaveDoMotor(estadoDoKit()), ligar.chaveDoMotor(estadoDoKit({ motor_diagnostico: diag('docker_parado') })));
});

test('tela Buscar: com o botão, o passo a passo manual fica recolhido; sem ele, aparece aberto', () => {
  const estado = estadoDoKit();
  const botao = ligar.criarLigarMotor({ estado, atualizarEstado: async () => estado, avisar: () => {} });
  const com = buscar.criarBlocoDoMotor(estado.motor_diagnostico, () => {}, botao);
  assert.match(textoTodo(com), /Ligar o motor/);
  assert.match(textoTodo(com), /Prefere ligar sozinho/);
  const sem = buscar.criarBlocoDoMotor(diag('docker_parado'), () => {}, null);
  assert.ok(!/Ligar o motor/.test(textoTodo(sem)));
  assert.ok(!/Prefere ligar sozinho/.test(textoTodo(sem)));
  assert.match(textoTodo(sem), /Passo um/);
});

test('o painel não tem texto de comando digitável para o botão', () => {
  assert.equal(instrucoes.COMANDO_LIGAR_MOTOR, 'docker compose up -d');
});
