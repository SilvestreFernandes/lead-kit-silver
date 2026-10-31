// Passo a passo para quem nunca abriu um terminal. Todo texto que manda a pessoa executar algo
// usa estas listas, para a explicação de onde e como ser sempre a mesma em todas as telas.
// A lista PASSOS_TERMINAL é a mesma de kit/diagnostico.py (um teste confere que são iguais).

export const COMANDO_LIGAR_KIT = 'python kit/servidor.py';
export const COMANDO_LIGAR_MOTOR = 'docker compose up -d';

export const PASSOS_TERMINAL = [
  'Abra a pasta do kit no Explorador de Arquivos (a pasta onde está o arquivo docker-compose.yml).',
  'Clique na barra de endereço, no alto da janela, apague o que estiver escrito, digite powershell e aperte Enter. Vai abrir uma janela escura.',
  'Clique no botão Copiar do comando, clique dentro da janela escura, aperte Ctrl e V juntos para colar, e aperte Enter.',
];

export const PASSOS_LIGAR_KIT = [
  ...PASSOS_TERMINAL,
  'Deixe a janela escura aberta enquanto usa o painel. Depois volte aqui e clique em Tentar de novo.',
];

export const PASSOS_LIGAR_MOTOR = [
  ...PASSOS_TERMINAL,
  'Espere uns 20 segundos e clique em Verificar de novo.',
];

export const PASSOS_DOCKER_PARADO = [
  'Abra o Docker Desktop pelo menu Iniciar (procure o ícone da baleia).',
  'Espere ele ficar verde. Pode levar um ou dois minutos.',
  ...PASSOS_LIGAR_MOTOR,
];

export const PASSOS_PERFIL_AUSENTE = [
  'Abra a sua IA (Claude Code, Codex ou a que você usou para instalar o kit). Se ela já estiver aberta, use a mesma janela.',
  'Veja se ela está dentro da pasta do Lead Kit Silver. Se não estiver, peça: "abra a pasta do Lead Kit Silver".',
  'Escreva para ela: "Faça a entrevista do meu perfil do Lead Kit Silver". Ela pergunta uma coisa de cada vez, e você responde com palavras simples.',
  'Quando ela disser que terminou, volte aqui e clique em Verificar de novo.',
];

// O que o servidor manda (motor_diagnostico) ou, se não mandou, o que vale para "motor desligado".
export function motivoDoMotor(diagnostico) {
  if (diagnostico && Array.isArray(diagnostico.passos)) return diagnostico;
  return {
    titulo: 'O motor de busca está desligado',
    texto: 'O motor de busca não está respondendo.',
    passos: PASSOS_LIGAR_MOTOR,
    comando: COMANDO_LIGAR_MOTOR,
  };
}
