// Aplica o tema salvo antes de o painel aparecer, para não piscar no tema errado.
// Carregado como script comum (não módulo) no <head>. Se o navegador não deixar guardar a escolha,
// o painel segue o tema do sistema.
(function () {
  try {
    var salvo = localStorage.getItem('lks-tema');
    if (salvo === 'light' || salvo === 'dark') document.documentElement.setAttribute('data-theme', salvo);
  } catch (erro) { /* sem armazenamento: segue o tema do sistema */ }
})();
