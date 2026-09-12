#!/usr/bin/env python3
"""Diagnostica a estrutura atual da busca do G1."""

import argparse
import collections
import os
import sys
from urllib import robotparser
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import config  # noqa: E402


def checar_robots(base_url: str, user_agent: str) -> None:
    rp = robotparser.RobotFileParser()
    try:
        resposta = requests.get(
            "https://g1.globo.com/robots.txt",
            headers=config.HEADERS,
            timeout=config.TIMEOUT_SEGUNDOS,
        )
        resposta.raise_for_status()
        rp.parse(resposta.text.splitlines())
        permitido = rp.can_fetch(user_agent, base_url)
        print(f"[robots.txt] Acesso a {base_url} permitido para o user-agent atual: {permitido}")
    except Exception as e:
        print(f"[robots.txt] Não foi possível ler robots.txt ({e}). Prossiga com cautela.")


def diagnosticar(termo: str, pagina: int, salvar_em: str) -> None:
    url = config.BASE_URL
    params = {"q": termo, "page": pagina}

    checar_robots(url, config.USER_AGENT)

    print(f"\n[requisição] GET {url}?{urlencode(params)}")
    resposta = requests.get(url, params=params, headers=config.HEADERS, timeout=config.TIMEOUT_SEGUNDOS)
    print(f"[resposta] status={resposta.status_code} content-type={resposta.headers.get('Content-Type')} "
          f"tamanho={len(resposta.text)} bytes")

    os.makedirs(os.path.dirname(salvar_em) or ".", exist_ok=True)
    with open(salvar_em, "w", encoding="utf-8") as f:
        f.write(resposta.text)
    print(f"[ok] HTML bruto salvo em {salvar_em}")

    html_lower = resposta.text.lower()
    termo_aparece = termo.lower() in html_lower
    print(f"\n[checagem] O termo buscado ('{termo}') aparece no HTML bruto: {termo_aparece}")
    if not termo_aparece:
        print(
            "  -> Forte indício de que os resultados são carregados via "
            "JavaScript/API (CSR), não via HTML renderizado no servidor. "
            "Abra a página no navegador, aba Rede (Network), filtre por "
            "'fetch/XHR' e procure a chamada que retorna os resultados em "
            "JSON — essa é provavelmente a fonte real dos dados."
        )

    soup = BeautifulSoup(resposta.text, "html.parser")

    for tag in ("article", "main", "script"):
        qtd = len(soup.find_all(tag))
        print(f"[estrutura] tags <{tag}>: {qtd}")

    print("\n[testando seletores candidatos configurados em src/config.py]")
    for candidato in config.SELECTOR_CANDIDATES:
        qtd = len(soup.select(candidato.container))
        marcador = "OK - possivelmente válido" if qtd > 0 else "sem correspondência"
        print(f"  - {candidato.nome:60s} container='{candidato.container[:40]}...' -> {qtd:3d} ({marcador})")

    print("\n[classes CSS mais frequentes na página] (top 25 — use como pista para achar o seletor certo)")
    contador = collections.Counter()
    for el in soup.find_all(class_=True):
        for classe in el.get("class", []):
            contador[classe] += 1
    for classe, freq in contador.most_common(25):
        print(f"  {freq:5d}  .{classe}")

    if termo_aparece:
        print(
            "\nPróximo passo sugerido: abra o arquivo salvo em um navegador ou "
            "editor, localize visualmente um card de resultado, confira a(s) "
            "classe(s) real(is) usada(s) e atualize SELECTOR_CANDIDATES em "
            "src/config.py com um candidato no topo da lista refletindo a "
            "estrutura atual."
        )
    else:
        print(
            "\nPróximo passo sugerido: validar a chamada de API usada pelo "
            "front-end. Em 2026-09-12, o componente de busca do G1 chamava "
            "POST https://busca.globo.com/v1/search; a rotina principal em "
            "src/scraper.py já usa essa fonte e mantém os seletores HTML "
            "apenas como fallback/regressão."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnostica a estrutura atual da página de busca do G1.")
    parser.add_argument("--termo", default=config.TERMO_BUSCA_PADRAO)
    parser.add_argument("--pagina", type=int, default=1)
    parser.add_argument("--salvar-em", default="diagnostico/pagina_bruta.html")
    args = parser.parse_args()
    diagnosticar(args.termo, args.pagina, args.salvar_em)
