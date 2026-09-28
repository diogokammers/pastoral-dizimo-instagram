// Rota do Cloudflare Pages: POST /api/resposta (lógica em lib/resposta.js; campos gerados por `python -m pastoral.links`).
import { tratar } from "../../lib/resposta.js";
import { CAMPOS } from "../../lib/campos.js";

export const onRequestPost = ({ request, env }) => tratar(request, env, new Date(), CAMPOS);
