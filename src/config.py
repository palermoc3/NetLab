"""Configurações da coleta G1."""

from dataclasses import dataclass
from typing import List

BASE_URL = "https://g1.globo.com/busca/"
SEARCH_API_URL = "https://busca.globo.com/v1/search"
SEARCH_PROFILE_PADRAO = "sp_g1_globo_com"
QUERY_ID_RECENTES = "g1.info_query_recency"
PAGE_SIZE_PADRAO = 10
TERMO_BUSCA_PADRAO = "lgpd"
TOTAL_PAGINAS_PADRAO = 5
TIMEOUT_SEGUNDOS = 15
MAX_TENTATIVAS = 3
BACKOFF_BASE_SEGUNDOS = 2.0
DELAY_ENTRE_REQUISICOES = (3.0, 6.0)
PARAR_APOS_PAGINAS_VAZIAS_SEGUIDAS = 2

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
    "NetLabUFRJ-ColetaLGPD/1.0 (+contato: equipe-netlab@ufrj.br)"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

API_HEADERS = {
    **HEADERS,
    "Content-Type": "application/json",
    "Origin": "https://g1.globo.com",
    "Referer": "https://g1.globo.com/busca/",
    "X-Tenant-Id": "g1",
    "X-Must-Thumborize": "true",
    "X-Track-Urls": "true",
}


@dataclass
class SeletorCandidato:
    nome: str
    container: str
    titulo: str
    resumo: str
    data: str
    link: str
    titulo_no_link: bool = False


SELECTOR_CANDIDATES: List[SeletorCandidato] = [
    SeletorCandidato(
        nome="bstn-feed (padrão de feed usado em várias páginas Globo)",
        container="div.widget--card, div.bstn-fd-item, div.bstn-hl-item",
        titulo="a.bstn-hl-item__link, a.widget--info__title, .feed-post-link",
        resumo=".widget--info__description, .feed-post-body-resumo",
        data=".widget--info__meta time, .feed-post-datetime, time",
        link="a",
    ),
    SeletorCandidato(
        nome="resultado-busca (padrão genérico de página de busca)",
        container="div.resultado-busca__item, li.resultado-busca__item, article.resultado-busca__item",
        titulo=".resultado-busca__titulo, h2, h3",
        resumo=".resultado-busca__subtitulo, .resultado-busca__resumo, p",
        data=".resultado-busca__data, time",
        link="a",
    ),
    SeletorCandidato(
        nome="fallback genérico (article/li com link+heading)",
        container="article, li.widget",
        titulo="h1, h2, h3",
        resumo="p",
        data="time",
        link="a",
    ),
    SeletorCandidato(
        nome="original do código legado (mantido só para referência/regressão)",
        container="div.resultado",
        titulo="div.titulo",
        resumo="p.resumo",
        data="span.data",
        link="a",
    ),
]


CAMPOS_OBRIGATORIOS = ("titulo", "url")

COLUNAS_SAIDA = [
    "id",
    "titulo",
    "resumo",
    "data_publicacao",
    "url",
    "pagina",
    "coletado_em",
    "seletor_usado",
]
