// ============================================
// PASSO 3: interações do painel, tudo em memória.
// Nada aqui fala com o backend de verdade ainda —
// isso é o Passo 4 (trocar por fetch() de verdade
// pro GET/POST/PUT/DELETE que o main.py já expõe).
// ============================================

// --------------------------------------------
// Estado fake, começando com as mesmas 2 linhas
// que já estavam fixas no HTML. Os nomes dos
// campos já batem com o schema real (models.py /
// schemas.py) pra facilitar a troca no Passo 4.
// --------------------------------------------
let proximoId = 3; // os ids 1 e 2 já "existem" nos itens abaixo

let itensFake = [
  {
    id: 1,
    tipo: "noticia",
    titulo: "UERN abre inscrições para bolsas de iniciação científica 2026",
    texto_original: "A Pró-Reitoria de Pesquisa e Pós-Graduação divulgou o edital com 200 vagas...",
    imagem_url: null,
    url_origem: "https://uern.br/noticias/exemplo-1",
    origem: "scraper",
    status: "ativo",
    data_publicacao: new Date("2026-08-17"),
    data_expiracao: null,
  },
  {
    id: 2,
    tipo: "edital",
    titulo: "Edital nº 042/2026 — Seleção de monitoria para o semestre 2026.2",
    texto_original: "Estão abertas as inscrições para monitoria voluntária e remunerada...",
    imagem_url: null,
    url_origem: null,
    origem: "manual",
    status: "oculto",
    data_publicacao: new Date("2026-08-12"),
    data_expiracao: null,
  },
];

// --------------------------------------------
// Referências ao DOM
// --------------------------------------------
const elBotoesModo = document.querySelectorAll(".seletor-modo__opcao");
const elStatusModoTexto = document.querySelector(".seletor-modo__status strong");
const elFormulario = document.querySelector(".formulario-conteudo");
const elTabelaCorpo = document.querySelector(".tabela-conteudos tbody");

// ============================================
// SELETOR DE MODO
// ============================================
elBotoesModo.forEach((botao) => {
  botao.addEventListener("click", () => {
    // tira "ativa" de todos, bota só no que foi clicado
    elBotoesModo.forEach((b) => b.classList.remove("seletor-modo__opcao--ativa"));
    botao.classList.add("seletor-modo__opcao--ativa");
    elStatusModoTexto.textContent = botao.textContent.trim();

    // Passo 4: aqui entra um fetch PUT /config { modo_atual: botao.dataset.modo }
  });
});

// ============================================
// FORMATAÇÃO — dd/mm/aaaa, igual já tava no HTML
// ============================================
function formatarData(data) {
  return data.toLocaleDateString("pt-BR");
}

// ============================================
// CONSTRÓI UMA LINHA DA TABELA
// Usa textContent (não innerHTML) pros campos que
// vêm de formulário — evita que texto digitado
// seja interpretado como HTML por acidente.
// ============================================
function criarLinha(item) {
  const linha = document.createElement("tr");

  // --- Tipo ---
  const tdTipo = document.createElement("td");
  const spanTipo = document.createElement("span");
  spanTipo.className = `etiqueta-tipo etiqueta-tipo--${item.tipo}`;
  spanTipo.textContent = item.tipo === "edital" ? "Edital" : "Notícia";
  tdTipo.appendChild(spanTipo);

  // --- Título ---
  const tdTitulo = document.createElement("td");
  tdTitulo.textContent = item.titulo;

  // --- Origem ---
  const tdOrigem = document.createElement("td");
  const spanOrigem = document.createElement("span");
  spanOrigem.className = `etiqueta-origem etiqueta-origem--${item.origem}`;
  spanOrigem.textContent = item.origem;
  tdOrigem.appendChild(spanOrigem);

  // --- Publicado em ---
  const tdData = document.createElement("td");
  tdData.textContent = formatarData(item.data_publicacao);

  // --- Status ---
  const tdStatus = document.createElement("td");
  const spanStatus = document.createElement("span");
  spanStatus.className = `etiqueta-status etiqueta-status--${item.status}`;
  spanStatus.textContent = item.status.charAt(0).toUpperCase() + item.status.slice(1);
  tdStatus.appendChild(spanStatus);

  // --- Ação (Ocultar / Reexibir) ---
  const tdAcao = document.createElement("td");
  const botaoAcao = document.createElement("button");
  botaoAcao.type = "button";
  botaoAcao.className = "botao botao--secundario botao--pequeno";
  botaoAcao.textContent = item.status === "ativo" ? "Ocultar" : "Reexibir";
  botaoAcao.addEventListener("click", () => alternarStatus(item.id));
  tdAcao.appendChild(botaoAcao);

  linha.append(tdTipo, tdTitulo, tdOrigem, tdData, tdStatus, tdAcao);
  return linha;
}

// ============================================
// REDESENHA A TABELA INTEIRA A PARTIR DO ARRAY
// (mais simples de raciocinar do que tentar editar
// só a linha que mudou — com poucas dezenas de itens
// o custo disso é irrelevante)
// ============================================
function renderizarTabela() {
  elTabelaCorpo.innerHTML = "";
  // mais recentes primeiro
  const itensOrdenados = [...itensFake].sort((a, b) => b.data_publicacao - a.data_publicacao);
  itensOrdenados.forEach((item) => {
    elTabelaCorpo.appendChild(criarLinha(item));
  });
}

// ============================================
// OCULTAR / REEXIBIR
// ============================================
function alternarStatus(id) {
  const item = itensFake.find((i) => i.id === id);
  if (!item) return;

  item.status = item.status === "ativo" ? "oculto" : "ativo";
  renderizarTabela();

  // Passo 4: aqui entra um fetch PUT /conteudos/{id} { status: novoStatus }
  // (ou DELETE /conteudos/{id}, que o backend já trata como "ocultar")
}

// ============================================
// FORMULÁRIO — adicionar novo conteúdo
// ============================================
elFormulario.addEventListener("submit", (evento) => {
  evento.preventDefault();

  const dados = new FormData(elFormulario);

  const novoItem = {
    id: proximoId++,
    tipo: dados.get("tipo"),
    titulo: dados.get("titulo").trim(),
    texto_original: dados.get("texto_original").trim(),
    imagem_url: dados.get("imagem_url") || null,
    url_origem: dados.get("url_origem") || null,
    origem: "manual",
    status: "ativo",
    data_publicacao: new Date(),
    data_expiracao: dados.get("data_expiracao") ? new Date(dados.get("data_expiracao")) : null,
  };

  itensFake.push(novoItem);
  renderizarTabela();
  elFormulario.reset();

  // Passo 4: aqui entra um fetch POST /conteudos com o corpo do formulário
});

// Primeira renderização, assim que a página carrega
renderizarTabela();