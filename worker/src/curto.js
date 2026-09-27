// Worker "aprovar" (ADR-012): link curto SEM código. https://aprovar.<subdomínio>.workers.dev/ redireciona
// para a página do painel. Não tem segredos, banco nem acesso ao GitHub; qualquer outra rota dá 404
// (inclusive a antiga /p/<código>, desativada).
import { redirecionarPagina } from "./acesso.js";

export default {
  fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" || request.method === "HEAD") {
      const r = redirecionarPagina(env, url);
      if (r) return r;
    }
    return new Response("Página não encontrada.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" },
    });
  },
};
