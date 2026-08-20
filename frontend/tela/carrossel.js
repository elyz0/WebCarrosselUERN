const API_BASE = "http://localhost:8000";
const DURACAO_SLIDE_MS = 10000;
const DURACAO_TRANSICAO_MS = 350;

const elBugModo = document.querySelector(".bug-institucional__modo");
const elCardAnterior = document.querySelector(".card-conteudo--anterior");
const elCardAtivo = document.querySelector(".card-conteudo--ativo");
const elCardProximo = document.querySelector(".card-conteudo--proximo");
const elBarraPreenchimento = document.querySelector(".barra-progresso__preenchimento");

if (elBarraPreenchimento) {
  elBarraPreenchimento.style.setProperty("--duracao-slide", `${DURACAO_SLIDE_MS / 1000}s`);
}

let indiceAtual = 0;
let itensAtivos = [];
let timerCarrossel = null;
let timerAtualizacao = null;

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
  const resposta = await fetch(`${API_BASE}/conteudos?status=ativo`);
  if (!resposta.ok) throw new Error("Nao foi possivel carregar os conteudos da TV.");

  const dados = await resposta.json();
  return Array.isArray(dados) ? dados.map(normalizarItem) : [];
}

function criarEstadoVazio(mensagem) {
  return {
    tipo: "noticia",
    categoria: "Sem conteudo",
    titulo: mensagem,
    resumo: "Adicione um conteudo pelo painel de suporte para iniciar o carrossel.",
    fonte: "Painel de suporte",
    data: "",
    tom: "azure",
  };
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
  const itemAtivo = pegarItem(0);
  const itemAnterior = pegarItem(-1);
  const itemProximo = pegarItem(1);

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

    itensAtivos = itens.length > 0 ? itens : [criarEstadoVazio(
      modoAtual === "edital" ? "Nenhum edital ativo" : "Nenhum conteudo ativo",
    )];

    if (indiceAtual >= itensAtivos.length) {
      indiceAtual = 0;
    }

    atualizarCarrossel();
  } catch (erro) {
    console.warn("Nao foi possivel atualizar o carrossel:", erro);
    itensAtivos = [criarEstadoVazio("Nao foi possivel carregar os conteudos")];
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

  timerAtualizacao = window.setInterval(() => {
    carregarDadosDoCarrossel();
  }, 5000);
}

window.addEventListener("DOMContentLoaded", iniciarCarrossel);
window.addEventListener("focus", carregarDadosDoCarrossel);
