# ADR-005 — Pré-estreia em produção, sem data fixa

Data: 2026-09-26. Status: aceito.

## Decisões do Diogo
1. **Hashtags fixas:** nenhuma por enquanto (`hashtags_fixas: []`).
2. **Post 3 ("Para onde vai o dízimo?"):** dimensões **religiosa, eclesial, missionária e caritativa** ("eclesial" substitui "social"). Continua proibido atribuir a síntese das quatro dimensões ao Doc. CNBB 106.
3. **Sem data de estreia.** Antes de qualquer pauta semanal, preparar o **pacote de estreia**: bio, capas dos 6 destaques e os 3 posts fixados, e pedir a **aprovação do Padre** responsável pela Pastoral.
   A conta só tem a equipe como seguidores, então o pacote pode ser publicado **em produção** para ver o resultado real e ser ajustado até a estreia. `semana_inicial: null` até lá.
4. Posts com dependência de dado real (3, 7, 9, 17, 19, 22, 28 da fila) ficam pendentes até o dado existir; nada é inventado.

## Consequências
- Aprovação em dois níveis na pré-estreia: Diogo (técnico) → Padre (conteúdo). A prévia HTML serve de material para o Padre.
- Bio e capas de destaques **não são publicáveis pela API** da Meta: o sistema gera os arquivos e o texto; a aplicação é manual no app (ou pelo Claude no navegador, com autorização).
- O post 3 perde a `pendencia` e entra no pacote de estreia.
