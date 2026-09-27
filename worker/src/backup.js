// Backup dos eventos do D1 no repositório (ADR-011): content/aprovacoes/eventos.jsonl, um evento por linha
// em JSON canônico, na ordem do id. Reescrito inteiro a partir do D1 (determinístico: sem mudança, sem
// commit). Roda depois de cada decisão (waitUntil) e todo dia pelo cron do Worker. Sem ip_hash.

import { ConflitoGitHub } from "./github.js";
import { canonicoTexto } from "./nucleo.js";

export const CAMINHO_BACKUP = "content/aprovacoes/eventos.jsonl";

export function jsonl(eventos) {
  return eventos.map((e) => canonicoTexto(e)).join("\n") + (eventos.length ? "\n" : "");
}

export async function exportarEventos(banco, gh) {
  const eventos = await banco.todos();
  const texto = jsonl(eventos);
  for (let tentativa = 1; ; tentativa++) {
    const atual = await gh.lerTextoComSha(CAMINHO_BACKUP);
    if (atual && atual.texto === texto) return { mudou: false, eventos: eventos.length, commit: null };
    if (!atual && !eventos.length) return { mudou: false, eventos: 0, commit: null };
    try {
      const commit = await gh.gravar(CAMINHO_BACKUP, texto,
        `aprovacoes: backup de ${eventos.length} evento(s) do D1`, atual?.sha);
      return { mudou: true, eventos: eventos.length, commit };
    } catch (erro) {
      if (erro instanceof ConflitoGitHub && tentativa < 3) continue;
      throw erro;
    }
  }
}
