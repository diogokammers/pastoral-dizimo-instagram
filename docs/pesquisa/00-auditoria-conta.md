# 00 — Auditoria da conta @pastoraldodizimo.arquifln

Data: 2026-09-25. Método: navegação autenticada no Chrome do Diogo (leitura, sem alterações).

## Estado observado
- **Perfil:** https://www.instagram.com/pastoraldodizimo.arquifln/ — nome "Pastoral do Dízimo | Arquidiocese Florianópolis".
- **Conteúdo:** 0 posts, 4 seguidores, 2 seguindo. Foto de perfil já definida (ícone vermelho com figuras/coração — não é marca oficial).
- **Bio (140/150 caracteres):** "Evangelizar, formar e fortalecer o dízimo como expressão de fé, gratidão e corresponsabilidade na missão da Igreja." Há uma menção "@pe…" truncada. Campo "Site" vazio (só editável pelo app).
- **Tipo de conta: PESSOAL.** Em *Configurações → Tipo e ferramentas da conta* aparece "Trocar para conta profissional", e a rota `/accounts/convert_to_professional_account/` oferece "Criador de conteúdo" / "Comercial". Ou seja, **ainda não é Business nem Creator**.
- **Central de Contas:** contém apenas o perfil do Instagram. **Nenhuma conta/Página do Facebook vinculada.**
- **E-mail de contato da conta:** pastoraldodizimo.arquifln@gmail.com. Data de nascimento cadastrada: adulta (dado pessoal omitido; relevante só porque contas "adolescentes" têm restrições — não é o caso).

## Implicações
1. Publicar por API exige conta **profissional** (Business ou Creator). A troca é feita pelo Diogo no app/web (decisão dele; sugestão: **Comercial/Business**, categoria "Organização religiosa", porque a doc da Meta trata Business como o caso padrão e permite botões de contato institucionais).
2. Sem Página do Facebook, a rota viável é **"Instagram API with Instagram Login"** (não exige Página) — a confirmar em `01-instagram-api.md`. Se a pesquisa mostrar limitação relevante nessa rota, a alternativa é criar uma Página e vincular.
3. O perfil está zerado: os "3 posts iniciais" + capas de destaques definem a primeira impressão. O estudo de identidade visual precisa vir **antes** do piloto.
4. A foto de perfil atual deve ser substituída pelo logotipo aprovado.
