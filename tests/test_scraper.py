import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scraper import G1BuscaScraper
from src.utils import texto_seguro, atributo_seguro
from bs4 import BeautifulSoup


FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "pagina_exemplo.html")
API_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "api_busca_exemplo.json")


@pytest.fixture
def html_exemplo():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def api_exemplo():
    with open(API_FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def scraper():
    return G1BuscaScraper(termo_busca="lgpd")


def test_parseia_cards_da_pagina_exemplo(scraper, html_exemplo):
    registros = scraper._parsear_pagina(html_exemplo, pagina=1)
    assert len(registros) == 4
    assert all(r.titulo for r in registros)
    assert all(r.url and r.url.startswith("https://g1.globo.com/") for r in registros)


def test_registro_sem_resumo_fica_incompleto_mas_nao_quebra(scraper, html_exemplo):
    registros = scraper._parsear_pagina(html_exemplo, pagina=1)
    sem_resumo = [r for r in registros if "ANPD" in (r.titulo or "")]
    assert len(sem_resumo) == 1
    assert sem_resumo[0].resumo is None
    assert "resumo" in sem_resumo[0].campos_ausentes()


def test_deduplicacao_remove_mesma_url_com_querystring_diferente(scraper, html_exemplo):
    registros = scraper._parsear_pagina(html_exemplo, pagina=1)
    unicos = scraper.deduplicar(registros)
    titulos = [r.titulo for r in unicos]
    assert titulos.count("Empresa é multada por descumprir LGPD") == 1
    assert len(unicos) == 3


def test_parseia_resposta_api_atual_do_g1(scraper, api_exemplo):
    registros = scraper._parsear_api(api_exemplo, pagina=1)

    assert len(registros) == 1
    assert registros[0].titulo == "ANPD multa TikTok por falhas na proteção de menores"
    assert registros[0].resumo == "Agência identificou infrações à LGPD."
    assert registros[0].data_publicacao == "2026-08-25T10:04:00.869Z"
    assert registros[0].url == (
        "https://g1.globo.com/tecnologia/noticia/2026/08/25/anpd-multa-tiktok.ghtml"
    )
    assert registros[0].seletor_usado == "api:busca.globo.com/v1/search"


def test_parseia_api_limpa_html_no_resumo(scraper):
    registro = scraper._extrair_registro_api(
        {
            "title": "Texto com destaque",
            "caption": "Cumprimento da <em>LGPD</em> no setor público.",
            "modified": "2026-08-20T12:00:00Z",
            "url": "https://g1.globo.com/exemplo.ghtml",
        },
        pagina=2,
    )

    assert registro.resumo == "Cumprimento da LGPD no setor público."
    assert registro.pagina == 2


def test_pagina_sem_resultados_conhecidos_retorna_lista_vazia(scraper):
    html_vazio = "<html><body><div class='algo-completamente-diferente'></div></body></html>"
    registros = scraper._parsear_pagina(html_vazio, pagina=1)
    assert registros == []


def test_texto_seguro_nao_quebra_com_tag_ausente():
    soup = BeautifulSoup("<div></div>", "html.parser")
    assert texto_seguro(soup.find("span")) is None


def test_atributo_seguro_nao_quebra_com_tag_ausente():
    soup = BeautifulSoup("<div></div>", "html.parser")
    assert atributo_seguro(soup.find("a"), "href") is None


@patch("src.scraper.requests.Session.get")
def test_requisitar_propaga_erro_http_4xx_sem_retry_infinito(mock_get, scraper):
    resposta_mock = MagicMock()
    resposta_mock.raise_for_status.side_effect = requests.HTTPError(
        response=MagicMock(status_code=404)
    )
    mock_get.return_value = resposta_mock

    with pytest.raises(Exception):
        scraper._requisitar(pagina=1)
    assert mock_get.call_count == 1


@patch("src.utils.time.sleep", return_value=None)
@patch("src.scraper.requests.Session.get")
def test_requisitar_tenta_novamente_em_http_5xx(mock_get, _sleep, scraper):
    resposta_mock = MagicMock()
    resposta_mock.raise_for_status.side_effect = requests.HTTPError(
        response=MagicMock(status_code=500)
    )
    mock_get.return_value = resposta_mock

    with pytest.raises(requests.HTTPError):
        scraper._requisitar(pagina=1)

    assert mock_get.call_count == 3


@patch("src.utils.time.sleep", return_value=None)
@patch("src.scraper.requests.Session.get")
def test_requisitar_tenta_novamente_em_timeout(mock_get, _sleep, scraper):
    mock_get.side_effect = requests.Timeout("tempo esgotado")

    with pytest.raises(requests.Timeout):
        scraper._requisitar(pagina=1)

    assert mock_get.call_count == 3


@patch("src.scraper.requests.Session.get")
def test_coletar_html_para_apos_paginas_vazias_seguidas(mock_get, scraper):
    resposta_mock = MagicMock()
    resposta_mock.text = "<html><body>sem resultados</body></html>"
    resposta_mock.raise_for_status.return_value = None
    mock_get.return_value = resposta_mock

    registros = scraper._coletar_via_html(total_paginas=5)
    assert registros == []
    assert mock_get.call_count <= 3


@patch("src.scraper.requests.Session.post")
def test_coletar_api_para_apos_paginas_vazias_seguidas(mock_post, scraper):
    scraper._api_config = scraper._api_config_padrao()
    resposta_mock = MagicMock()
    resposta_mock.json.return_value = [{"result": {"hits": {"hits": []}}}]
    resposta_mock.raise_for_status.return_value = None
    mock_post.return_value = resposta_mock

    registros = scraper._coletar_via_api(total_paginas=5, page_size=10)

    assert registros == []
    assert mock_post.call_count <= 3
