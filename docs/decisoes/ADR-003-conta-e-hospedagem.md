# ADR-003 — Conta profissional, repositório público e pendências institucionais

Data: 2026-09-26. Status: aceito.

## Decisões do Diogo (2026-09-26)
1. **Conta do Instagram trocada para profissional** (Comercial, categoria "Igreja Católica" — mais precisa que
   "Organização religiosa"; categoria **não** exibida no perfil). Feito por Claude no Chrome do Diogo com autorização.
   Sem informações de contato públicas e **sem** vínculo com Página do Facebook (rota Instagram Login não exige).
   Efeito colateral da Meta: o perfil passa a ser público.
2. **Repositório público** → GitHub Pages hospeda imagens (`image_url`) e prévia, sem Cloudflare para isso.
   Antes de publicar, retirar dados pessoais do histórico (ver R11).
3. **`CLAUDE_CODE_OAUTH_TOKEN`:** Diogo gera com `claude setup-token` quando a fatia 3 precisar.
4. **Manual de marca da Arquidiocese (R8):** seguir sem, por enquanto.
5. **E-mail institucional e WhatsApp:** seguir sem, por enquanto (perfil sem botões de contato).
6. **Doc. CNBB 106 (R7):** localizado — ver [06-cnbb-doc-106.md](../pesquisa/06-cnbb-doc-106.md).

## Pendentes com o Diogo
- Criar o app na Meta (tipo Business, nome sugerido "Pastoral Dizimo Publicador") — a criação automática foi
  bloqueada pelo modo de permissão desta sessão.
- Criar contas Resend e Cloudflare.

## Novo risco
| # | Item | Impacto | Como fechar |
|---|---|---|---|
| R11 | Histórico git contém dado pessoal (data de nascimento em `00-auditoria-conta.md`) | Alto se o repo for público | Remover do arquivo e reescrever o histórico antes de tornar público (decisão do Diogo) |
