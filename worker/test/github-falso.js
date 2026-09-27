// GitHub falso para os testes: um `fetch` que responde à Contents API e a /dispatches a partir de um
// repositório em memória (caminho → bytes). Registra cada chamada; nada sai para a rede.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { deBase64, deUtf8, paraBase64, utf8 } from "../src/nucleo.js";

export const RAIZ_REPO = fileURLToPath(new URL("../../", import.meta.url));
export const FIXTURE = join(RAIZ_REPO, "tests", "fixtures", "semana-exemplo");
export const VETORES = JSON.parse(readFileSync(join(RAIZ_REPO, "tests", "fixtures", "vetores-python.json"), "utf8"));

export function arquivosDaFixture(pasta = FIXTURE) {
  const mapa = new Map();
  const andar = (dir) => {
    for (const nome of readdirSync(dir)) {
      const cheio = join(dir, nome);
      if (statSync(cheio).isDirectory()) andar(cheio);
      else if (!nome.startsWith("aprovacao")) mapa.set(relative(pasta, cheio).split(sep).join("/"), readFileSync(cheio));
    }
  };
  andar(pasta);
  return mapa;
}

let contadorSha = 0;

export class GitHubFalso {
  constructor(arquivos = arquivosDaFixture(), repo = "diogokammers/pastoral-dizimo-instagram") {
    this.arquivos = new Map([...arquivos].map(([k, v]) => [k, { bytes: new Uint8Array(v), sha: `sha${++contadorSha}` }]));
    this.repo = repo;
    this.chamadas = [];
    this.gravacoes = [];
    this.disparos = [];
    this.conflitosPendentes = 0; // quantos PUT seguidos devolvem 409
    this.erroEm = null; // { metodo, status, corpo } para simular falha
    this.fetch = this.fetch.bind(this);
  }

  texto(caminho) {
    return deUtf8(this.arquivos.get(caminho).bytes);
  }

  async fetch(url, init = {}) {
    const metodo = init.method || "GET";
    const u = new URL(url);
    this.chamadas.push({ metodo, url: u.pathname + u.search, headers: init.headers });
    if (this.erroEm && this.erroEm.metodo === metodo) return new Response(this.erroEm.corpo, { status: this.erroEm.status });
    const prefixo = `/repos/${this.repo}`;
    if (!u.pathname.startsWith(prefixo)) return new Response("repo errado", { status: 404 });
    const resto = u.pathname.slice(prefixo.length);
    if (resto === "/dispatches" && metodo === "POST") {
      this.disparos.push(JSON.parse(init.body));
      return new Response(null, { status: 204 });
    }
    if (!resto.startsWith("/contents/")) return new Response("?", { status: 404 });
    const caminho = decodeURIComponent(resto.slice("/contents/".length));
    const atual = this.arquivos.get(caminho);
    if (metodo === "GET") {
      if (!atual) return new Response('{"message":"Not Found"}', { status: 404 });
      if (init.headers.Accept === "application/vnd.github.raw+json") return new Response(atual.bytes, { status: 200 });
      return Response.json({ sha: atual.sha, content: paraBase64(atual.bytes).replace(/(.{60})/g, "$1\n") });
    }
    if (metodo === "PUT") {
      const corpo = JSON.parse(init.body);
      if (this.conflitosPendentes > 0) {
        this.conflitosPendentes--;
        return new Response('{"message":"sha does not match"}', { status: 409 });
      }
      if ((atual && corpo.sha !== atual.sha) || (!atual && corpo.sha)) {
        return new Response('{"message":"sha does not match"}', { status: 409 });
      }
      const bytes = deBase64(corpo.content);
      this.arquivos.set(caminho, { bytes, sha: `sha${++contadorSha}` });
      const commit = `commit${++contadorSha}`;
      this.gravacoes.push({ caminho, texto: deUtf8(bytes), mensagem: corpo.message, ramo: corpo.branch, commit });
      return Response.json({ content: { path: caminho }, commit: { sha: commit } }, { status: atual ? 200 : 201 });
    }
    return new Response("método", { status: 405 });
  }
}

export const ENV = {
  GITHUB_REPO: "diogokammers/pastoral-dizimo-instagram",
  GITHUB_BRANCH: "master",
  APROVADO_POR: "Diogo",
  PREVIA_BASE_URL: "https://diogokammers.github.io/pastoral-dizimo-instagram/",
  LINK_HMAC_SECRET: "segredo-link-de-teste",
  APROVACAO_HMAC_SECRET: "segredo-aprovacao-de-teste",
  GH_PAT_WORKER: "github_pat_TESTE_NAO_REAL",
};

export { utf8 };
