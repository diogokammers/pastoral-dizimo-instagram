# ADR-002 — Identidade visual: paleta e tipografia aprovadas; logotipo adiado

Data: 2026-09-26. Status: aceito.

## Contexto
Estudo em [identidade-visual.md](../marca/identidade-visual.md): 7 rodadas de símbolo (`assets/marca/propostas/`),
paleta derivada do Brasão da Arquidiocese e par tipográfico com licença SIL OFL.

## Decisões do Diogo (2026-09-26)
1. **Logotipo:** fica o que está no perfil hoje. Nenhuma das propostas das rodadas 1–7 é adotada agora;
   os arquivos ficam em `assets/marca/propostas/` para retomada futura.
2. **Paleta aprovada:** vermelho `#A3121C` + vermelho profundo `#7E0F17` + prata `#F3F2EE` + grafite/cinza
   + dourado só em filetes (tokens do §3 do estudo).
3. **Tipografia aprovada:** Cormorant Garamond 600 (títulos) + Source Sans 3 400/600 (apoio).
4. **Foto de perfil:** mantida por enquanto.

## Consequências
- A fatia 4 (templates + render) está **desbloqueada**. Os templates usam **assinatura tipográfica**
  ("Pastoral do Dízimo" + "@pastoraldodizimo.arquifln") no lugar do símbolo; o símbolo é um slot opcional
  em `config.yaml` (`marca.simbolo: null`), para trocar sem refazer templates quando houver logotipo.
- Nenhum template reproduz o símbolo atual do perfil (origem em outra diocese; ver estudo §1).
- Capas de destaques: ícones de linha na paleta aprovada, sem símbolo.
