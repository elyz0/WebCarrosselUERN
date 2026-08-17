// ============================================
// PASSO 3: lógica do carrossel com dados fake.
// No Passo 4 isso vira uma função que busca de
// GET /conteudos em vez de ler esse array fixo.
// ============================================

// Quanto tempo (em ms) cada item fica na tela antes de trocar.
// Vira segundos lá no CSS pra bater com a duração da animação da barra.
const DURACAO_SLIDE_MS = 10000;

// Duração da transição de fade/slide do conteúdo (precisa bater com o
// "transition" definido em .card-conteudo__miolo no CSS).
const DURACAO_TRANSICAO_MS = 350;

// --------------------------------------------
// Dados fake — troque por dados reais no Passo 4.
// "tom" escolhe a variação visual do card (azure /
// azure-claro / ciano), só pra dar variedade ao ciclar.
// --------------------------------------------
const itensFake = [
  {
    tipo: "noticia",
    categoria: "Notícia",
    titulo: "UERN abre inscrições para bolsas de iniciação científica 2026",
    resumo: "A Pró-Reitoria de Pesquisa e Pós-Graduação divulgou o edital com 200 vagas de bolsas de iniciação científica para estudantes de graduação de todos os campi. As inscrições vão até o dia 30 de setembro pelo portal do estudante.",
    fonte: "Portal UERN",
    data: "17 de agosto de 2026",
    tom: "azure",
  },
  {
    tipo: "noticia",
    categoria: "Notícia",
    titulo: "Campus de Mossoró recebe semana de acolhimento aos calouros",
    resumo: "Entre os dias 25 e 29 de agosto, a UERN promove atividades de integração para estudantes ingressantes, com apresentação dos setores, oficinas e roda de conversa com veteranos.",
    fonte: "Portal UERN",
    data: "15 de agosto de 2026",
    tom: "azure-claro",
  },
  {
    tipo: "edital",
    categoria: "Edital",
    titulo: "Edital nº 042/2026 — Seleção de monitoria para o semestre 2026.2",
    resumo: "Estão abertas as inscrições para monitoria voluntária e remunerada em diversas disciplinas de graduação. Prazo final para envio de documentação: 5 de setembro.",
    fonte: "Editais UERN",
    data: "12 de agosto de 2026",
    tom: "ciano",
  },
];

// --------------------------------------------
// Referências aos elementos do DOM (pegas uma vez só)
// --------------------------------------------
const elBugModo = document.querySelector(".bug-institucional__modo");
const elCardAnterior = document.querySelector(".card-conteudo--anterior");
const elCardAtivo = document.querySelector(".card-conteudo--ativo");
const elCardProximo = document.querySelector(".card-conteudo--proximo");
const elBarraPreenchimento = document.querySelector(".barra-progresso__preenchimento");

// A barra de progresso lê essa variável CSS pra saber quanto tempo animar.
elBarraPreenchimento.style.setProperty("--duracao-slide", `${DURACAO_SLIDE_MS / 1000}s`);

let indiceAtual = 0;

// Pega o item da lista com um deslocamento (-1 = anterior, +1 = próximo),
// dando a volta no início/fim do array (por isso o "% total").
function pegarItem(deslocamento) {
  const total = itensFake.length;
  const indice = (indiceAtual + deslocamento + total) % total;
  return itensFake[indice];
}

// Preenche o card ATIVO (o único com texto legível de verdade).
function preencherCardAtivo(card, item) {
  card.dataset.tom = item.tom;
  card.querySelector(".card-conteudo__fantasma").textContent = item.categoria.toUpperCase();
  card.querySelector(".card-conteudo__categoria").textContent = item.categoria;
  card.querySelector(".card-conteudo__titulo").textContent = item.titulo;
  card.querySelector(".card-conteudo__resumo").textContent = item.resumo;
  card.querySelector(".card-conteudo__fonte").textContent = item.fonte;
  card.querySelector(".card-conteudo__data").textContent = item.data;
}

// Preenche um card PEEK (anterior/próximo) — só precisa do tom e do
// texto-fantasma, já que o resto fica cortado/ilegível mesmo.
function preencherCardPeek(card, item) {
  card.dataset.tom = item.tom;
  card.querySelector(".card-conteudo__fantasma").textContent = item.categoria.toUpperCase();
}

// Ajusta a largura e a posição da barra conforme o número de itens.
// Cada passo ocupa uma fração do total: se há 3 itens, 33.33%; se há 5,
// 20%; e a barra se desloca à direita em cada avanço, voltando ao início
// quando o ciclo completa.
function reiniciarBarraProgresso() {
  const totalItens = Math.max(itensFake.length, 1);
  const tamanhoPasso = 100 / totalItens;
  const deslocamento = indiceAtual * tamanhoPasso;

  elBarraPreenchimento.style.setProperty("--barra-tamanho", `${tamanhoPasso}%`);
  elBarraPreenchimento.style.setProperty("--barra-offset", `${deslocamento}%`);
}

// Passo central: esconde o conteúdo atual (transição), troca os dados
// por baixo, e revela de novo — dando a sensação de slide.
function atualizarCarrossel() {
  const itemAnterior = pegarItem(-1);
  const itemAtivo = pegarItem(0);
  const itemProximo = pegarItem(1);

  elBugModo.textContent = itemAtivo.tipo === "edital" ? "Editais" : "Notícias";

  elCardAnterior.classList.add("card-conteudo--trocando");
  elCardAtivo.classList.add("card-conteudo--trocando");
  elCardProximo.classList.add("card-conteudo--trocando");

  window.setTimeout(() => {
    preencherCardPeek(elCardAnterior, itemAnterior);
    preencherCardAtivo(elCardAtivo, itemAtivo);
    preencherCardPeek(elCardProximo, itemProximo);

    // Espera o próximo frame antes de remover a classe, senão o
    // navegador às vezes "funde" as duas mudanças e a transição não roda.
    requestAnimationFrame(() => {
      elCardAnterior.classList.remove("card-conteudo--trocando");
      elCardAtivo.classList.remove("card-conteudo--trocando");
      elCardProximo.classList.remove("card-conteudo--trocando");
    });

    reiniciarBarraProgresso();
  }, DURACAO_TRANSICAO_MS);
}

// Primeira renderização, assim que a página carrega.
atualizarCarrossel();

// A cada DURACAO_SLIDE_MS, avança um item e atualiza a tela.
window.setInterval(() => {
  indiceAtual = (indiceAtual + 1) % itensFake.length;
  atualizarCarrossel();
}, DURACAO_SLIDE_MS);