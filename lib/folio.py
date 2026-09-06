# -*- coding: utf-8 -*-
"""
Biblioteca compartilhada de acesso à API do FOLIO (BIBLION / RVBI).

Toda configuração vem de variável de ambiente:
  - valores NÃO sensíveis -> ConfigMap  (scripts-common.yaml)
  - senhas                -> Secret     (adm-rvbi-scripts-secrets)

Trata os dois modelos de autenticação do FOLIO:
  - Okapi  (legado): POST /authn/login              -> header x-okapi-token
  - Eureka (atual) : POST /authn/login-with-expiry   -> cookies + expiração curta

O BIBLION está em migração de Okapi para Eureka. Esta biblioteca detecta
o modelo em uso e renova o token sozinha, que é o ponto onde os scripts
antigos quebram (o token do Eureka dura poucos minutos).
"""
import logging
import os
import time
from datetime import datetime, timedelta

import requests

log = logging.getLogger(__name__)

BASE_URL = os.getenv("FOLIO_BASE_URL", "").rstrip("/")
TENANT = os.getenv("FOLIO_TENANT", "")
USERNAME = os.getenv("FOLIO_USERNAME", "")
PASSWORD = os.getenv("FOLIO_PASSWORD", "")
TIMEOUT = int(os.getenv("FOLIO_TIMEOUT", "60"))
MARGEM_RENOVACAO_SEG = int(os.getenv("FOLIO_MARGEM_RENOVACAO_SEG", "60"))


class FolioError(RuntimeError):
    """Erro de comunicação ou autenticação com o FOLIO."""


class FolioClient:
    """Cliente HTTP do FOLIO com renovação automática de token."""

    def __init__(self, base_url=None, tenant=None, username=None, password=None):
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.tenant = tenant or TENANT
        self.username = username or USERNAME
        self.password = password or PASSWORD

        faltando = [n for n, v in (
            ("FOLIO_BASE_URL", self.base_url),
            ("FOLIO_TENANT", self.tenant),
            ("FOLIO_USERNAME", self.username),
            ("FOLIO_PASSWORD", self.password),
        ) if not v]
        if faltando:
            raise FolioError(
                "Configuração incompleta. Variáveis ausentes: " + ", ".join(faltando)
            )

        self.sessao = requests.Session()
        self.token = None
        self.expira_em = None

    # ------------------------------------------------------------- login
    def login(self):
        """Autentica. Tenta o fluxo Eureka primeiro; cai para o Okapi."""
        corpo = {"username": self.username, "password": self.password}
        cabecalho = {"Content-Type": "application/json", "x-okapi-tenant": self.tenant}

        # Eureka: token de vida curta, devolvido em cookie
        try:
            r = self.sessao.post(
                f"{self.base_url}/authn/login-with-expiry",
                json=corpo, headers=cabecalho, timeout=TIMEOUT,
            )
            if r.status_code in (200, 201):
                self.token = (
                    self.sessao.cookies.get("folioAccessToken")
                    or r.headers.get("x-okapi-token")
                )
                if self.token:
                    self.expira_em = datetime.now() + timedelta(minutes=8)
                    log.info("Login OK (fluxo Eureka).")
                    return self.token
        except requests.RequestException:
            pass  # endpoint pode não existir em tenant Okapi

        # Okapi: token no header
        r = self.sessao.post(
            f"{self.base_url}/authn/login",
            json=corpo, headers=cabecalho, timeout=TIMEOUT,
        )
        if r.status_code not in (200, 201):
            raise FolioError(f"Falha no login: HTTP {r.status_code} — {r.text[:300]}")

        self.token = r.headers.get("x-okapi-token")
        if not self.token:
            try:
                self.token = r.json().get("okapiToken")
            except ValueError:
                self.token = None
        if not self.token:
            raise FolioError("Login respondeu, mas nenhum token foi devolvido.")

        self.expira_em = datetime.now() + timedelta(minutes=8)
        log.info("Login OK (fluxo Okapi).")
        return self.token

    def get_token(self):
        vencido = (
            not self.token
            or not self.expira_em
            or datetime.now() >= self.expira_em - timedelta(seconds=MARGEM_RENOVACAO_SEG)
        )
        if vencido:
            self.login()
        return self.token

    def headers(self, extra=None):
        h = {
            "x-okapi-tenant": self.tenant,
            "x-okapi-token": self.get_token(),
            "Accept": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    # -------------------------------------------------------- requisições
    def get(self, caminho, params=None, tentativas=3):
        """GET com retentativa. Devolve (json, tempo_de_resposta_em_segundos)."""
        ultimo_erro = None
        for tentativa in range(1, tentativas + 1):
            inicio = time.perf_counter()
            try:
                r = self.sessao.get(
                    f"{self.base_url}{caminho}",
                    headers=self.headers(), params=params or {}, timeout=TIMEOUT,
                )
                decorrido = time.perf_counter() - inicio

                if r.status_code == 401 and tentativa < tentativas:
                    log.warning("HTTP 401 — renovando token e tentando de novo.")
                    self.token = None
                    continue

                r.raise_for_status()
                return r.json(), decorrido

            except requests.RequestException as e:
                ultimo_erro = e
                if tentativa < tentativas:
                    espera = 2 ** tentativa
                    log.warning("Erro %s. Nova tentativa em %ss.", type(e).__name__, espera)
                    time.sleep(espera)

        raise FolioError(f"GET {caminho} falhou após {tentativas} tentativas: {ultimo_erro}")

    def get_todos(self, caminho, chave, query=None, pagina=200, maximo=None):
        """
        GET paginado. A API do FOLIO nunca devolve tudo de uma vez — quem
        esquece disso escreve relatório que só considera os primeiros registros.
        """
        registros, offset = [], 0
        while True:
            params = {"limit": pagina, "offset": offset}
            if query:
                params["query"] = query
            dados, _ = self.get(caminho, params)
            lote = dados.get(chave, [])
            registros.extend(lote)
            total = dados.get("totalRecords", 0)
            offset += pagina
            if not lote or offset >= total or (maximo and len(registros) >= maximo):
                break
        return registros[:maximo] if maximo else registros

    def contar(self, caminho, query=None):
        """Conta registros sem baixá-los (limit=0 devolve só o total)."""
        params = {"limit": 0}
        if query:
            params["query"] = query
        dados, _ = self.get(caminho, params)
        return dados.get("totalRecords", 0)


def conectar():
    """Cria o cliente e valida a conexão imediatamente, falhando cedo."""
    cliente = FolioClient()
    cliente.login()
    return cliente
