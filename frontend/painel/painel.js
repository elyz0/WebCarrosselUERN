// ============================================
// PASSO 3: interações do painel, tudo em memória.
// Nada aqui fala com o backend de verdade ainda —
// isso é o Passo 4 (trocar por fetch() de verdade
// pro GET/POST/PUT/DELETE que o main.py já expõe).
// ============================================
const API_BASE = window.API_BASE || "http://localhost:8000";

let itens = [];

const elBotoesModo = document.querySelectorAll(".seletor-modo__opcao");
const elStatusModoTexto = document.querySelector(".seletor-modo__status strong");
const elFormulario = document.querySelector(".formulario-conteudo");
const elTabelaCorpo = document.querySelector(".tabela-conteudos tbody");
const elBotaoSincronizar = document.querySelector("#botao-sincronizar");
const elStatusSincronizar = document.querySelector("#status-sincronizar");

async function requisicaoApi(caminho, opcoes = {}) {
  const resposta = await fetch(`${API_BASE}${caminho}`, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });

  if (!resposta.ok) {
    let detalhe = `Erro ${resposta.status}`;
    try {
      const erro = await resposta.json();
      detalhe = erro.detail || detalhe;
    } catch {
      // Mantem a mensagem de status quando a resposta nao e JSON.
    }
    throw new Error(detalhe);
  }

  return resposta.status === 204 ? null : resposta.json();
}

function mostrarErro(erro) {
  console.error(erro);
  window.alert(`Nao foi possivel concluir a operacao: ${erro.message}`);
}

function selecionarModo(modo) {
  elBotoesModo.forEach((botao) => {
    const ativo = botao.dataset.modo === modo;
    botao.classList.toggle("seletor-modo__opcao--ativa", ativo);
    botao.setAttribute("aria-checked", String(ativo));
  });
  elStatusModoTexto.textContent = modo === "edital" ? "Edital" : "Geral";
}

elBotoesModo.forEach((botao) => {
  botao.setAttribute("role", "radio");
  botao.addEventListener("click", async () => {
    const modo = botao.dataset.modo;
    elBotoesModo.forEach((item) => { item.disabled = true; });

    try {
      const config = await requisicaoApi("/config", {
        method: "PUT",
        body: JSON.stringify({ modo_atual: modo }),
      });
      selecionarModo(config.modo_atual);
    } catch (erro) {
      mostrarErro(erro);
    } finally {
      elBotoesModo.forEach((item) => { item.disabled = false; });
    }
  });
});

function formatarData(data) {
  const dataFormatada = new Date(data);
  return Number.isNaN(dataFormatada.getTime()) ? "-" : dataFormatada.toLocaleDateString("pt-BR");
}

function criarLinha(item) {
  const linha = document.createElement("tr");

  const tdTipo = document.createElement("td");
  const spanTipo = document.createElement("span");
  spanTipo.className = `etiqueta-tipo etiqueta-tipo--${item.tipo}`;
  spanTipo.textContent = item.tipo === "edital" ? "Edital" : "Noticia";
  tdTipo.appendChild(spanTipo);

  const tdTitulo = document.createElement("td");
  tdTitulo.textContent = item.titulo;

  const tdOrigem = document.createElement("td");
  const spanOrigem = document.createElement("span");
  spanOrigem.className = `etiqueta-origem etiqueta-origem--${item.origem}`;
  spanOrigem.textContent = item.origem;
  tdOrigem.appendChild(spanOrigem);

  const tdData = document.createElement("td");
  tdData.textContent = formatarData(item.data_publicacao);

  const tdStatus = document.createElement("td");
  const spanStatus = document.createElement("span");
  spanStatus.className = `etiqueta-status etiqueta-status--${item.status}`;
  spanStatus.textContent = item.status.charAt(0).toUpperCase() + item.status.slice(1);
  tdStatus.appendChild(spanStatus);

  const tdAcao = document.createElement("td");
  if (item.status === "ativo" || item.status === "oculto") {
    const botaoAcao = document.createElement("button");
    botaoAcao.type = "button";
    botaoAcao.className = "botao botao--secundario botao--pequeno";
    botaoAcao.textContent = item.status === "ativo" ? "Ocultar" : "Reexibir";
    botaoAcao.addEventListener("click", () => alternarStatus(item, botaoAcao));
    tdAcao.appendChild(botaoAcao);
  }

  linha.append(tdTipo, tdTitulo, tdOrigem, tdData, tdStatus, tdAcao);
  return linha;
}

function renderizarTabela() {
  elTabelaCorpo.replaceChildren();
  const itensOrdenados = [...itens].sort(
    (a, b) => new Date(b.data_publicacao) - new Date(a.data_publicacao),
  );
  itensOrdenados.forEach((item) => elTabelaCorpo.appendChild(criarLinha(item)));
}

async function alternarStatus(item, botao) {
  const novoStatus = item.status === "ativo" ? "oculto" : "ativo";
  botao.disabled = true;

  try {
    const itemAtualizado = await requisicaoApi(`/conteudos/${item.id}`, {
      method: "PUT",
      body: JSON.stringify({ status: novoStatus }),
    });
    itens = itens.map((conteudo) => conteudo.id === item.id ? itemAtualizado : conteudo);
    renderizarTabela();
  } catch (erro) {
    mostrarErro(erro);
    botao.disabled = false;
  }
}

elBotaoSincronizar.addEventListener("click", async () => {
  elBotaoSincronizar.disabled = true;
  elStatusSincronizar.textContent = "Lendo o RSS do portal...";

  try {
    const resultado = await requisicaoApi("/scraper/sincronizar", { method: "POST" });
    const falhas = (resultado.fontes || []).filter((fonte) => fonte.erro);
    const vias = (resultado.fontes || [])
      .filter((fonte) => fonte.via)
      .map((fonte) => `${fonte.nome} via ${fonte.via}`)
      .join("; ");

    elStatusSincronizar.textContent = [
      `${resultado.novos} novo(s)`,
      `${resultado.ignorados} já existia(m)`,
      vias,
      falhas.length ? `falha: ${falhas.map((fonte) => fonte.nome).join(", ")}` : "",
    ].filter(Boolean).join(" · ");

    await carregarPainel();
  } catch (erro) {
    elStatusSincronizar.textContent = "";
    mostrarErro(erro);
  } finally {
    elBotaoSincronizar.disabled = false;
  }
});

elFormulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const botaoEnviar = elFormulario.querySelector("button[type='submit']");
  const dados = new FormData(elFormulario);
  const payload = {
    tipo: dados.get("tipo"),
    titulo: dados.get("titulo").trim(),
    texto_original: dados.get("texto_original").trim(),
    imagem_url: dados.get("imagem_url") || null,
    url_origem: dados.get("url_origem") || null,
    data_expiracao: dados.get("data_expiracao") || null,
  };

  botaoEnviar.disabled = true;
  try {
    const novoItem = await requisicaoApi("/conteudos", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    itens.push(novoItem);
    renderizarTabela();
    elFormulario.reset();
  } catch (erro) {
    mostrarErro(erro);
  } finally {
    botaoEnviar.disabled = false;
  }
});

async function carregarPainel() {
  try {
    const [config, conteudos] = await Promise.all([
      requisicaoApi("/config"),
      requisicaoApi("/conteudos?status="),
    ]);
    selecionarModo(config.modo_atual);
    itens = conteudos;
    renderizarTabela();
  } catch (erro) {
    mostrarErro(erro);
  }
}

carregarPainel();

