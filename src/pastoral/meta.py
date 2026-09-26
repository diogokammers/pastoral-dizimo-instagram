"""Cliente mínimo da Meta — Instagram API with Instagram Login (host graph.instagram.com). ADR-008.

Só o que o portão de publicação precisa: contêiner de imagem (ou item de carrossel), contêiner de
carrossel, poll do `status_code`, `media_publish`, `permalink`, `refresh_access_token` e `GET /me`.

Segurança:
- Token e user id vêm SÓ das variáveis de ambiente `IG_ACCESS_TOKEN` e `IG_USER_ID`.
- Em POST o token vai no corpo, nunca na URL. Em GET ele vai na query (exigência da API), e a URL
  nunca é impressa.
- Toda mensagem de erro passa por `mascarar`, que troca o token por "***".

Uso (diagnóstico, não publica nada):
    python -m pastoral.meta --verificar            # GET /me?fields=user_id,username
    python -m pastoral.meta --renovar --saida ARQ  # refresh_access_token; grava o token novo em ARQ
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

import yaml

HOST = "https://graph.instagram.com"
VERSAO = "v26.0"
RAIZ = Path(__file__).resolve().parents[2]


class ErroMeta(RuntimeError):
    """Erro da API ou de configuração, com o token já mascarado."""


def mascarar(texto: str, token: str) -> str:
    """Troca o token por *** (nada a fazer se o token estiver vazio)."""
    texto = str(texto)
    return texto.replace(token, "***") if token else texto


def transporte_urllib(metodo: str, url: str, dados: bytes | None) -> tuple[int, bytes]:
    """Faz o pedido HTTP com a biblioteca padrão; devolve (status, corpo) também em erro HTTP."""
    pedido = urllib.request.Request(url, data=dados, method=metodo)
    if dados is not None:
        pedido.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read()


class ClienteMeta:
    def __init__(self, token: str, user_id: str, versao: str = VERSAO, host: str = HOST,
                 transporte=None, dormir=time.sleep):
        if not token or not user_id:
            raise ErroMeta("token e user id são obrigatórios")
        self._token = token
        self.user_id = str(user_id)
        self.versao = versao
        self.host = host.rstrip("/")
        # Resolve na hora da chamada para os testes poderem trocar `transporte_urllib`.
        self._transporte = transporte
        self._dormir = dormir

    def __repr__(self) -> str:
        return f"ClienteMeta(user_id={self.user_id!r}, versao={self.versao!r}, token=***)"

    @classmethod
    def do_ambiente(cls, config: dict | None = None, **kw) -> "ClienteMeta":
        """Cria o cliente a partir de IG_ACCESS_TOKEN / IG_USER_ID e da seção `meta` do config."""
        token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
        user_id = os.environ.get("IG_USER_ID", "").strip()
        faltando = [n for n, v in (("IG_ACCESS_TOKEN", token), ("IG_USER_ID", user_id)) if not v]
        if faltando:
            raise ErroMeta("variável de ambiente ausente: " + ", ".join(faltando))
        m = (config or {}).get("meta", {})
        return cls(token, user_id, versao=m.get("versao_api", VERSAO), host=m.get("host", HOST), **kw)

    # ---------- HTTP ----------

    def _pedir(self, metodo: str, caminho: str, params: dict, versionado: bool = True) -> dict:
        base = f"{self.host}/{self.versao}" if versionado else self.host
        url = f"{base}/{caminho.lstrip('/')}"
        params = {**params, "access_token": self._token}
        if metodo == "GET":
            url, dados = f"{url}?{urlencode(params)}", None
        else:
            dados = urlencode(params).encode("utf-8")
        transporte = self._transporte or transporte_urllib
        try:
            status, corpo = transporte(metodo, url, dados)
        except Exception as erro:  # rede, DNS, timeout: a mensagem pode conter a URL com o token
            raise ErroMeta(mascarar(f"falha de rede em {metodo} /{caminho}: {erro}", self._token)) from None
        try:
            resposta = json.loads(corpo.decode("utf-8")) if corpo else {}
        except ValueError:
            resposta = {"bruto": corpo[:300].decode("utf-8", "replace")}
        if status >= 400 or "error" in resposta:
            erro = resposta.get("error", resposta)
            if isinstance(erro, dict):
                detalhe = f"{erro.get('message', '')} (code {erro.get('code')}, subcode {erro.get('error_subcode')})"
            else:
                detalhe = str(erro)
            raise ErroMeta(mascarar(f"HTTP {status} em {metodo} /{caminho}: {detalhe}", self._token))
        return resposta

    def _id(self, resposta: dict) -> str:
        if "id" not in resposta:
            raise ErroMeta(mascarar(f"resposta sem id: {resposta}", self._token))
        return str(resposta["id"])

    # ---------- publicação ----------

    def criar_item_carrossel(self, image_url: str, alt_text: str | None = None) -> str:
        params = {"image_url": image_url, "is_carousel_item": "true"}
        if alt_text:
            params["alt_text"] = alt_text
        return self._id(self._pedir("POST", f"{self.user_id}/media", params))

    def criar_imagem(self, image_url: str, caption: str, alt_text: str | None = None) -> str:
        params = {"image_url": image_url, "caption": caption}
        if alt_text:
            params["alt_text"] = alt_text
        return self._id(self._pedir("POST", f"{self.user_id}/media", params))

    def criar_carrossel(self, children: list[str], caption: str) -> str:
        if not 2 <= len(children) <= 10:
            raise ErroMeta(f"carrossel precisa de 2 a 10 itens (recebeu {len(children)})")
        params = {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption}
        return self._id(self._pedir("POST", f"{self.user_id}/media", params))

    def status(self, container_id: str) -> str:
        return self._pedir("GET", container_id, {"fields": "status_code"}).get("status_code", "")

    def aguardar(self, container_id: str, intervalo: float = 60, maximo: float = 300) -> None:
        """Poll do status até FINISHED. ERROR/EXPIRED ou estouro do tempo levantam ErroMeta."""
        esperado = 0.0
        while True:
            estado = self.status(container_id)
            if estado in ("FINISHED", "PUBLISHED"):
                return
            if estado in ("ERROR", "EXPIRED"):
                raise ErroMeta(f"contêiner {container_id} com status {estado}")
            if esperado + intervalo > maximo:
                raise ErroMeta(f"contêiner {container_id} passou do tempo máximo ({maximo:.0f} s) em {estado}")
            self._dormir(intervalo)
            esperado += intervalo

    def media_publish(self, creation_id: str) -> str:
        return self._id(self._pedir("POST", f"{self.user_id}/media_publish", {"creation_id": creation_id}))

    def permalink(self, media_id: str) -> str | None:
        return self._pedir("GET", media_id, {"fields": "permalink"}).get("permalink")

    # ---------- conta e token ----------

    def me(self) -> dict:
        return self._pedir("GET", "me", {"fields": "user_id,username"})

    def refresh_access_token(self) -> dict:
        """Renova o token longo (+60 dias). Endpoint sem versão, conforme a doc do Instagram Login."""
        return self._pedir("GET", "refresh_access_token", {"grant_type": "ig_refresh_token"}, versionado=False)


def carregar_config(caminho: Path = RAIZ / "config.yaml") -> dict:
    return yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Diagnóstico e renovação do token da Meta (não publica nada).")
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--verificar", action="store_true", help="GET /me?fields=user_id,username")
    grupo.add_argument("--renovar", action="store_true", help="refresh_access_token (grant_type=ig_refresh_token)")
    ap.add_argument("--saida", help="arquivo onde gravar o token renovado (obrigatório com --renovar)")
    ap.add_argument("--config", default=str(RAIZ / "config.yaml"))
    args = ap.parse_args(argv)
    try:
        cliente = ClienteMeta.do_ambiente(carregar_config(Path(args.config)), transporte=transporte_urllib)
        if args.verificar:
            dados = cliente.me()
            print(f"Token válido. user_id={dados.get('user_id')} username={dados.get('username')}")
            if str(dados.get("user_id", "")) not in ("", cliente.user_id):
                print(f"Atenção: IG_USER_ID ({cliente.user_id}) difere do user_id do token.")
                return 1
            return 0
        if not args.saida:
            print("--renovar exige --saida ARQUIVO (o token novo nunca é impresso).", file=sys.stderr)
            return 2
        dados = cliente.refresh_access_token()
        novo = dados.get("access_token")
        if not novo:
            print("Resposta sem access_token.", file=sys.stderr)
            return 1
        Path(args.saida).write_text(novo, encoding="utf-8")
        dias = int(dados.get("expires_in", 0)) // 86400
        print(f"Token renovado; validade de {dias} dias. Gravado em {args.saida}.")
        if dias < 10:
            print(f"::warning::Token vale só {dias} dias.")
        return 0
    except ErroMeta as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
