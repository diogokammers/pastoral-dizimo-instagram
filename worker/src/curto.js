// Worker "aprovar" (ADR-011): só o link curto /p/<código> → página do painel com o código no fragmento.
// Não tem segredos, banco nem acesso ao GitHub; qualquer outra rota dá 404. O Worker principal
// (pastoral-dizimo-aprovacao) continua respondendo /a, /api e também /p/.
import { redirecionarCurto } from "./acesso.js";

export default {
  fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" || request.method === "HEAD") {
      const r = redirecionarCurto(env, url);
      if (r) return r;
    }
    return new Response("Página não encontrada.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" },
    });
  },
};
