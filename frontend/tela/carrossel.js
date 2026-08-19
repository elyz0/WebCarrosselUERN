const API_BASE = "http://localhost:8000";
const DURACAO_SLIDE_MS = 10000;
const DURACAO_TRANSICAO_MS = 350;

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

const elBugModo = document.querySelector(".bug-institucional__modo");
const elCardAnterior = document.querySelector(".card-conteudo--anterior");
const elCardAtivo = document.querySelector(".card-conteudo--ativo");
const elCardProximo = document.querySelector(".card-conteudo--proximo");
const elBarraPreenchimento = document.querySelector(".barra-progresso__preenchimento");

if (elBarraPreenchimento) {
  elBarraPreenchimento.style.setProperty("--duracao-slide", `${DURACAO_SLIDE_MS / 1000}s`);
}

let indiceAtual = 0;
let itensAtivos = [...itensFake];
let timerCarrossel = null;

function formatarData(dataString) {
  if (!dataString) return "Sem data";

  const data = new Date(dataString);
  if (Number.isNaN(data.getTime())) return dataString;

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(data);
}

function normalizarItem(item) {
  const tipo = item.tipo === "edital" ? "edital" : "noticia";
  const categoria = tipo === "edital" ? "Edital" : "Notícia";

  return {
    tipo,
    categoria,
    titulo: item.titulo || "Sem título",
    resumo: item.resumo || item.texto_original || "Sem resumo disponível.",
    fonte: item.origem === "manual" ? "Painel de suporte" : "Portal UERN",
    data: formatarData(item.data_publicacao || item.data_expiracao || item.data),
    tom: tipo === "edital" ? "ciano" : (Math.random() > 0.5 ? "azure" : "azure-claro"),
  };
}

async function carregarModo() {
  const resposta = await fetch(`${API_BASE}/config`);
  if (!resposta.ok) {
    throw new Error("Não foi possível carregar o modo da TV.");
  }

  const config = await resposta.json();
  const modoAtual = config.modo_atual === "edital" ? "edital" : "geral";

  if (elBugModo) {
    elBugModo.textContent = modoAtual === "edital" ? "Editais" : "Notícias";
  }

  return modoAtual;
}

async function carregarConteudos() {
  try {
    const resposta = await fetch(`${API_BASE}/conteudos`);
    if (!resposta.ok) throw new Error("Falha no backend");

    const dados = await resposta.json();
    const itens = Array.isArray(dados) ? dados.filter((item) => item.status !== "oculto") : [];
    const normalizados = itens.map(normalizarItem);
    return normalizados.length ? normalizados : [...itensFake];
  } catch (erro) {
    console.warn("Carrossel usando fallback:", erro);
    return [...itensFake];
  }
}

function pegarItem(deslocamento) {
  const total = itensAtivos.length || 1;
  const indice = (indiceAtual + deslocamento + total) % total;
  return itensAtivos[indice];
}

function preencherCardAtivo(card, item) {
  if (!card || !item) return;

  card.dataset.tom = item.tom;
  card.querySelector(".card-conteudo__fantasma").textContent = item.categoria.toUpperCase();
  card.querySelector(".card-conteudo__categoria").textContent = item.categoria;
  card.querySelector(".card-conteudo__titulo").textContent = item.titulo;
  card.querySelector(".card-conteudo__resumo").textContent = item.resumo;
  card.querySelector(".card-conteudo__fonte").textContent = item.fonte;
  card.querySelector(".card-conteudo__data").textContent = item.data;
}

function preencherCardPeek(card, item) {
  if (!card || !item) return;

  card.dataset.tom = item.tom;
  card.querySelector(".card-conteudo__fantasma").textContent = item.categoria.toUpperCase();
}

function reiniciarBarraProgresso() {
  if (!elBarraPreenchimento) return;

  const totalItens = Math.max(itensAtivos.length, 1);
  const tamanhoPasso = 100 / totalItens;
  const deslocamento = indiceAtual * tamanhoPasso;

  elBarraPreenchimento.style.setProperty("--barra-tamanho", `${tamanhoPasso}%`);
  elBarraPreenchimento.style.setProperty("--barra-offset", `${deslocamento}%`);
}

function atualizarCarrossel() {
  const itemAnterior = pegarItem(-1);
  const itemAtivo = pegarItem(0);
  const itemProximo = pegarItem(1);

  if (elBugModo) {
    elBugModo.textContent = itemAtivo.tipo === "edital" ? "Editais" : "Notícias";
  }

  elCardAnterior.classList.add("card-conteudo--trocando");
  elCardAtivo.classList.add("card-conteudo--trocando");
  elCardProximo.classList.add("card-conteudo--trocando");

  window.setTimeout(() => {
    preencherCardPeek(elCardAnterior, itemAnterior);
    preencherCardAtivo(elCardAtivo, itemAtivo);
    preencherCardPeek(elCardProximo, itemProximo);

    requestAnimationFrame(() => {
      elCardAnterior.classList.remove("card-conteudo--trocando");
      elCardAtivo.classList.remove("card-conteudo--trocando");
      elCardProximo.classList.remove("card-conteudo--trocando");
    });

    reiniciarBarraProgresso();
  }, DURACAO_TRANSICAO_MS);
}

async function carregarDadosDoCarrossel() {
  try {
    const modoAtual = await carregarModo();
    let itens = await carregarConteudos();

    if (modoAtual === "edital") {
      itens = itens.filter((item) => item.tipo === "edital");
    }

    itensAtivos = itens.length > 0 ? itens : [...itensFake];

    if (indiceAtual >= itensAtivos.length) {
      indiceAtual = 0;
    }

    atualizarCarrossel();
  } catch (erro) {
    console.warn("Fallback do carrossel:", erro);
    itensAtivos = [...itensFake];
    atualizarCarrossel();
  }
}

function iniciarCarrossel() {
  carregarDadosDoCarrossel();

  if (timerCarrossel) {
    clearInterval(timerCarrossel);
  }

  timerCarrossel = window.setInterval(() => {
    if (!itensAtivos.length) return;
    indiceAtual = (indiceAtual + 1) % itensAtivos.length;
    atualizarCarrossel();
  }, DURACAO_SLIDE_MS);

  window.setInterval(() => {
    carregarDadosDoCarrossel();
  }, 5000);
}

window.addEventListener("DOMContentLoaded", iniciarCarrossel);
window.addEventListener("focus", iniciarCarrossel);
