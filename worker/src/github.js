// Cliente mínimo da GitHub REST API (Contents + repository_dispatch) para o Worker (ADR-009).
// O PAT (GH_PAT_WORKER, fine-grained, contents:write só neste repositório) nunca aparece em mensagens.

import { deBase64, deUtf8, paraBase64, utf8 } from "./nucleo.js";

const API = "https://api.github.com";

export class ErroGitHub extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.status = status;
  }
}

export class ConflitoGitHub extends ErroGitHub {}

const caminhoUrl = (caminho) => caminho.split("/").map(encodeURIComponent).join("/");

export class GitHub {
  constructor(env, fetchFn) {
    this.repo = env.GITHUB_REPO;
    this.ramo = env.GITHUB_BRANCH || "master";
    this.token = (env.GH_PAT_WORKER || "").trim();
    this.fetch = fetchFn;
    if (!this.repo || !this.token) throw new ErroGitHub("GITHUB_REPO ou GH_PAT_WORKER não configurado", 500);
  }

  mascarar(texto) {
    return this.token ? String(texto).split(this.token).join("***") : String(texto);
  }

  async pedir(metodo, caminho, { accept = "application/vnd.github+json", corpo } = {}) {
    const headers = {
      Authorization: `Bearer ${this.token}`,
      Accept: accept,
      "User-Agent": "pastoral-dizimo-aprovacao",
      "X-GitHub-Api-Version": "2022-11-28",
    };
    if (corpo !== undefined) headers["Content-Type"] = "application/json";
    return this.fetch(`${API}/repos/${this.repo}${caminho}`, {
      method: metodo,
      headers,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  }

  async falha(resposta, oQue) {
    let detalhe = "";
    try {
      detalhe = (await resposta.text()).slice(0, 200);
    } catch {
      /* sem corpo */
    }
    return new ErroGitHub(this.mascarar(`GitHub ${resposta.status} ao ${oQue}: ${detalhe}`), resposta.status);
  }

  // Conteúdo bruto (até 100 MB) — usado para as artes e JSONs da semana.
  async lerBytes(caminho) {
    const r = await this.pedir("GET", `/contents/${caminhoUrl(caminho)}?ref=${encodeURIComponent(this.ramo)}`, {
      accept: "application/vnd.github.raw+json",
    });
    if (!r.ok) throw await this.falha(r, `ler ${caminho}`);
    return new Uint8Array(await r.arrayBuffer());
  }

  async lerJson(caminho) {
    return JSON.parse(deUtf8(await this.lerBytes(caminho)));
  }

  // Arquivo pequeno (até 1 MB) com o sha do blob (necessário para atualizar). null se não existe.
  async lerTextoComSha(caminho) {
    const r = await this.pedir("GET", `/contents/${caminhoUrl(caminho)}?ref=${encodeURIComponent(this.ramo)}`);
    if (r.status === 404) return null;
    if (!r.ok) throw await this.falha(r, `ler ${caminho}`);
    const meta = await r.json();
    return { sha: meta.sha, texto: deUtf8(deBase64(meta.content || "")) };
  }

  async lerJsonComSha(caminho) {
    const atual = await this.lerTextoComSha(caminho);
    return atual && { sha: atual.sha, dados: JSON.parse(atual.texto) };
  }

  // Cria ou atualiza com commit e devolve o sha do commit. 409/422 (sha desatualizado) viram ConflitoGitHub.
  async gravar(caminho, texto, mensagem, sha) {
    const corpo = { message: mensagem, content: paraBase64(utf8(texto)), branch: this.ramo };
    if (sha) corpo.sha = sha;
    const r = await this.pedir("PUT", `/contents/${caminhoUrl(caminho)}`, { corpo });
    if (r.status === 409 || r.status === 422) {
      const erro = await this.falha(r, `gravar ${caminho}`);
      throw new ConflitoGitHub(erro.message, r.status);
    }
    if (!r.ok) throw await this.falha(r, `gravar ${caminho}`);
    try {
      return (await r.json())?.commit?.sha ?? null;
    } catch {
      return null;
    }
  }

  async disparar(evento, payload) {
    const r = await this.pedir("POST", "/dispatches", { corpo: { event_type: evento, client_payload: payload } });
    if (r.status !== 204 && !r.ok) throw await this.falha(r, `disparar ${evento}`);
  }
}
