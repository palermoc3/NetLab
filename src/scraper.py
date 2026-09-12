"""Coleta resultados da busca do G1 por API, com fallback HTML."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlsplit
import json
import random
import re
import time

import requests
from bs4 import BeautifulSoup

from . import config
from .models import Noticia, _normalizar_url
from .utils import logger, retry_com_backoff, texto_seguro, atributo_seguro


class G1BuscaScraper:
    def __init__(
        self,
        termo_busca: str = config.TERMO_BUSCA_PADRAO,
        base_url: str = config.BASE_URL,
        session: Optional[requests.Session] = None,
    ):
        self.termo_busca = termo_busca
        self.base_url = base_url
        self.session = session or requests.Session()
        self.session.headers.update(config.HEADERS)
        self._api_config: Optional[Dict[str, Any]] = None

    @retry_com_backoff(config.MAX_TENTATIVAS, config.BACKOFF_BASE_SEGUNDOS)
    def _requisitar_html(self, pagina: int) -> requests.Response:
        params = {"q": self.termo_busca, "page": pagina}
        logger.info("Baixando HTML da busca página %d (termo=%r)...", pagina, self.termo_busca)
        resposta = self.session.get(
            self.base_url, params=params, timeout=config.TIMEOUT_SEGUNDOS
        )
        resposta.raise_for_status()
        logger.info("Página %d: HTML retornou HTTP %d.", pagina, resposta.status_code)
        return resposta

    _requisitar = _requisitar_html

    @retry_com_backoff(config.MAX_TENTATIVAS, config.BACKOFF_BASE_SEGUNDOS)
    def _requisitar_api(self, pagina: int, page_size: int) -> requests.Response:
        cfg = self._api_config or self._api_config_padrao()
        inicio = (pagina - 1) * page_size
        payload = [
            {
                "search_profile": cfg["search_profile"],
                "query": cfg["query_id"],
                "params": {
                    "q": self.termo_busca,
                    "from": inicio,
                    "size": page_size,
                },
            }
        ]
        headers = {**config.API_HEADERS, "X-Tenant-Id": cfg["tenant_id"]}
        logger.info(
            "Coletando via API página %d (from=%d, size=%d, termo=%r)...",
            pagina,
            inicio,
            page_size,
            self.termo_busca,
        )
        resposta = self.session.post(
            cfg["search_api_url"],
            headers=headers,
            json=payload,
            timeout=config.TIMEOUT_SEGUNDOS,
        )
        resposta.raise_for_status()
        logger.info("Página %d: API retornou HTTP %d.", pagina, resposta.status_code)
        return resposta

    def _api_config_padrao(self) -> Dict[str, str]:
        return {
            "search_api_url": config.SEARCH_API_URL,
            "tenant_id": "g1",
            "search_profile": config.SEARCH_PROFILE_PADRAO,
            "query_id": config.QUERY_ID_RECENTES,
        }

    def _descobrir_api_config(self) -> Dict[str, str]:
        if self._api_config:
            return self._api_config

        try:
            resposta = self._requisitar_html(1)
            self._api_config = self._extrair_api_config(resposta.text)
        except requests.RequestException as e:
            logger.warning(
                "Não foi possível baixar HTML para descobrir a API (%s). "
                "Usando configuração padrão conhecida.",
                e,
            )
            self._api_config = self._api_config_padrao()

        logger.info(
            "API de busca configurada: %s (profile=%s, query=%s).",
            self._api_config["search_api_url"],
            self._api_config["search_profile"],
            self._api_config["query_id"],
        )
        return self._api_config

    def _extrair_api_config(self, html: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        contexto = None
        for script in soup.find_all("script"):
            texto = script.string or script.get_text()
            if "window.__CONTEXT__=" not in texto:
                continue
            match = re.search(r"window\.__CONTEXT__=(.*)$", texto.strip(), re.S)
            if not match:
                continue
            contexto = json.loads(match.group(1))
            break

        if not contexto:
            logger.warning(
                "HTML não contém window.__CONTEXT__; usando configuração padrão da API."
            )
            return self._api_config_padrao()

        recurso = contexto.get("api_content", {}).get("resource", {})
        cfg = recurso.get("config", {})
        env = contexto.get("environment", {}).get("env", "prod")
        search_api_url = config.SEARCH_API_URL

        if env != "prod":
            logger.warning("Ambiente inesperado no contexto do G1: %s", env)

        query_ids = cfg.get("queryId", {})
        return {
            "search_api_url": search_api_url,
            "tenant_id": recurso.get("tenantId") or "g1",
            "search_profile": cfg.get("searchProfile") or config.SEARCH_PROFILE_PADRAO,
            "query_id": query_ids.get("recent") or config.QUERY_ID_RECENTES,
        }

    def _parsear_pagina(self, html: str, pagina: int) -> List[Noticia]:
        soup = BeautifulSoup(html, "html.parser")

        for candidato in config.SELECTOR_CANDIDATES:
            containers = soup.select(candidato.container)
            if containers:
                logger.debug(
                    "Página %d: seletor '%s' encontrou %d cards.",
                    pagina, candidato.nome, len(containers),
                )
                break
        else:
            logger.warning(
                "Página %d: nenhum seletor candidato encontrou resultados. "
                "A estrutura HTML pode ter mudado novamente — rode "
                "scripts/diagnostico.py para investigar.",
                pagina,
            )
            return []

        registros: List[Noticia] = []
        for card in containers:
            registro = self._extrair_registro(card, candidato, pagina)
            faltando = [c for c in config.CAMPOS_OBRIGATORIOS if not getattr(registro, c)]
            if faltando:
                logger.warning(
                    "Página %d: registro descartado por falta de campo(s) obrigatório(s) %s.",
                    pagina, faltando,
                )
                continue
            if registro.campos_ausentes():
                logger.info(
                    "Página %d: registro '%s' coletado com campo(s) incompleto(s): %s",
                    pagina, (registro.titulo or "")[:60], registro.campos_ausentes(),
                )
            registros.append(registro)

        return registros

    def _extrair_registro(self, card, candidato, pagina: int) -> Noticia:
        link_tag = card.select_one(candidato.link)
        url = atributo_seguro(link_tag, "href")
        if url:
            url = urljoin(self.base_url, url)

        if candidato.titulo_no_link:
            titulo = texto_seguro(link_tag)
        else:
            titulo = texto_seguro(card.select_one(candidato.titulo)) or texto_seguro(link_tag)

        resumo = texto_seguro(card.select_one(candidato.resumo))
        data_tag = card.select_one(candidato.data)
        data_publicacao = (
            atributo_seguro(data_tag, "datetime") or texto_seguro(data_tag)
        )

        return Noticia(
            titulo=titulo,
            resumo=resumo,
            data_publicacao=data_publicacao,
            url=url,
            pagina=pagina,
            coletado_em=datetime.now(),
            seletor_usado=candidato.nome,
        )

    def _parsear_api(self, payload: Any, pagina: int) -> List[Noticia]:
        if isinstance(payload, dict):
            blocos = [payload]
        elif isinstance(payload, list):
            blocos = payload
        else:
            logger.warning("Página %d: resposta da API com formato inesperado.", pagina)
            return []

        bloco_principal = next((b for b in blocos if isinstance(b, dict) and b.get("result")), {})
        result = bloco_principal.get("result") or {}
        hits = (((result.get("hits") or {}).get("hits")) or [])
        registros: List[Noticia] = []

        for hit in hits:
            source = hit.get("_source") or {}
            registro = self._extrair_registro_api(source, pagina)
            faltando = [c for c in config.CAMPOS_OBRIGATORIOS if not getattr(registro, c)]
            if faltando:
                logger.warning(
                    "Página %d: item da API descartado por falta de campo(s) obrigatório(s) %s.",
                    pagina,
                    faltando,
                )
                continue
            if registro.campos_ausentes():
                logger.info(
                    "Página %d: registro '%s' coletado com campo(s) incompleto(s): %s",
                    pagina,
                    (registro.titulo or "")[:60],
                    registro.campos_ausentes(),
                )
            registros.append(registro)

        return registros

    def _extrair_registro_api(self, source: Dict[str, Any], pagina: int) -> Noticia:
        resumo = (
            source.get("caption")
            or source.get("description")
            or (source.get("page_indexer_message") or {}).get("description")
            or source.get("subtitle")
            or source.get("subtitulo")
        )
        data_publicacao = source.get("issued") or source.get("modified")
        url = self._normalizar_url_api(source.get("url"))

        return Noticia(
            titulo=source.get("title"),
            resumo=self._limpar_texto_api(resumo),
            data_publicacao=data_publicacao,
            url=url,
            pagina=pagina,
            coletado_em=datetime.now(),
            seletor_usado="api:busca.globo.com/v1/search",
        )

    @staticmethod
    def _normalizar_url_api(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        partes = urlsplit(url)
        if partes.netloc == "measures.globo.com":
            destino = parse_qs(partes.query).get("u", [None])[0]
            return destino or url
        return url

    @staticmethod
    def _limpar_texto_api(valor: Optional[str]) -> Optional[str]:
        if not valor:
            return None
        soup = BeautifulSoup(str(valor), "html.parser")
        texto = soup.get_text(" ", strip=True)
        return texto or None

    @staticmethod
    def deduplicar(registros: List[Noticia]) -> List[Noticia]:
        vistos = set()
        unicos = []
        duplicados = 0
        for r in registros:
            chave = _normalizar_url(r.url) if r.url else r.titulo
            if chave in vistos:
                duplicados += 1
                continue
            vistos.add(chave)
            unicos.append(r)
        if duplicados:
            logger.info("Removidos %d registro(s) duplicado(s).", duplicados)
        return unicos

    def coletar(self, total_paginas: int = config.TOTAL_PAGINAS_PADRAO) -> List[Noticia]:
        self._descobrir_api_config()
        try:
            return self._coletar_via_api(total_paginas=total_paginas)
        except requests.RequestException as e:
            logger.error(
                "Coleta via API falhou definitivamente (%s). Tentando fallback HTML.",
                e,
            )
            return self._coletar_via_html(total_paginas=total_paginas)

    def _coletar_via_api(
        self,
        total_paginas: int = config.TOTAL_PAGINAS_PADRAO,
        page_size: int = config.PAGE_SIZE_PADRAO,
    ) -> List[Noticia]:
        resultados: List[Noticia] = []
        paginas_vazias_seguidas = 0

        for pagina in range(1, total_paginas + 1):
            try:
                resposta = self._requisitar_api(pagina, page_size)
                registros_pagina = self._parsear_api(resposta.json(), pagina)
            except ValueError as e:
                logger.error("Página %d: JSON inválido na resposta da API (%s).", pagina, e)
                registros_pagina = []
            except requests.RequestException as e:
                logger.error("Página %d: falha definitiva na API após retries (%s).", pagina, e)
                raise

            if not registros_pagina:
                paginas_vazias_seguidas += 1
                if paginas_vazias_seguidas >= config.PARAR_APOS_PAGINAS_VAZIAS_SEGUIDAS:
                    logger.info(
                        "%d página(s) vazias seguidas na API — encerrando coleta.",
                        paginas_vazias_seguidas,
                    )
                    break
            else:
                paginas_vazias_seguidas = 0

            resultados.extend(registros_pagina)
            logger.info("Página %d: %d registro(s) coletado(s) via API.", pagina, len(registros_pagina))

            if pagina < total_paginas:
                espera = random.uniform(*config.DELAY_ENTRE_REQUISICOES)
                time.sleep(espera)

        resultados = self.deduplicar(resultados)
        logger.info("Coleta finalizada: %d registro(s) únicos.", len(resultados))
        return resultados

    def _coletar_via_html(self, total_paginas: int = config.TOTAL_PAGINAS_PADRAO) -> List[Noticia]:
        resultados: List[Noticia] = []
        paginas_vazias_seguidas = 0

        for pagina in range(1, total_paginas + 1):
            try:
                resposta = self._requisitar_html(pagina)
            except requests.RequestException as e:
                logger.error("Página %d: falha definitiva após retries (%s). Pulando.", pagina, e)
                paginas_vazias_seguidas += 1
                if paginas_vazias_seguidas >= config.PARAR_APOS_PAGINAS_VAZIAS_SEGUIDAS:
                    logger.warning("Muitas falhas seguidas — encerrando coleta antecipadamente.")
                    break
                continue

            registros_pagina = self._parsear_pagina(resposta.text, pagina)

            if not registros_pagina:
                paginas_vazias_seguidas += 1
                if paginas_vazias_seguidas >= config.PARAR_APOS_PAGINAS_VAZIAS_SEGUIDAS:
                    logger.info(
                        "%d página(s) vazias seguidas — assumindo fim dos resultados.",
                        paginas_vazias_seguidas,
                    )
                    break
            else:
                paginas_vazias_seguidas = 0

            resultados.extend(registros_pagina)
            logger.info("Página %d: %d registro(s) coletado(s).", pagina, len(registros_pagina))

            if pagina < total_paginas:
                espera = random.uniform(*config.DELAY_ENTRE_REQUISICOES)
                time.sleep(espera)

        resultados = self.deduplicar(resultados)
        logger.info("Coleta finalizada: %d registro(s) únicos.", len(resultados))
        return resultados
