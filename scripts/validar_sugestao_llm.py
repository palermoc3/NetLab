#!/usr/bin/env python3
"""Valida sugestões de LLM contra dados brutos HTML ou JSON."""

import argparse
import json
import os
import sys
from typing import Any

from bs4 import BeautifulSoup


def carregar_json(caminho: str) -> Any:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def carregar_texto(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def valores_por_caminho(obj: Any, caminho: str) -> list:
    partes = caminho.split(".")
    atuais = [obj]
    for parte in partes:
        proximos = []
        lista = parte.endswith("[]")
        chave = parte[:-2] if lista else parte
        for atual in atuais:
            candidatos = atual if isinstance(atual, list) else [atual]
            for candidato in candidatos:
                if not isinstance(candidato, dict) or chave not in candidato:
                    continue
                valor = candidato[chave]
                if lista:
                    if isinstance(valor, list):
                        proximos.extend(valor)
                else:
                    proximos.append(valor)
        atuais = proximos
    return atuais


def validar_json(dados: Any, sugestao: dict) -> list:
    erros = []
    campos = sugestao.get("campos")
    if not isinstance(campos, dict):
        return ["Sugestão JSON precisa conter objeto 'campos'."]

    for campo, caminho in campos.items():
        if not isinstance(caminho, str) or not caminho.strip():
            erros.append(f"Campo {campo}: caminho vazio ou inválido.")
            continue
        valores = valores_por_caminho(dados, caminho)
        if not valores:
            erros.append(f"Campo {campo}: caminho não encontrado ({caminho}).")
            continue
        if not any(v not in (None, "", []) for v in valores):
            erros.append(f"Campo {campo}: caminho encontrado, mas sem valores úteis.")
    return erros


def validar_html(html: str, sugestao: dict) -> list:
    erros = []
    seletores = sugestao.get("seletores")
    if not isinstance(seletores, dict):
        return ["Sugestão HTML precisa conter objeto 'seletores'."]

    soup = BeautifulSoup(html, "html.parser")
    for campo, seletor in seletores.items():
        if not isinstance(seletor, str) or not seletor.strip():
            erros.append(f"Campo {campo}: seletor vazio ou inválido.")
            continue
        try:
            elementos = soup.select(seletor)
        except Exception as e:
            erros.append(f"Campo {campo}: seletor CSS inválido ({e}).")
            continue
        if not elementos:
            erros.append(f"Campo {campo}: seletor não encontrou elementos ({seletor}).")
    return erros


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida sugestão estruturada de LLM.")
    parser.add_argument("--dados-brutos", required=True)
    parser.add_argument("--sugestao", required=True)
    parser.add_argument("--tipo", choices=["json", "html"], required=True)
    args = parser.parse_args()

    if not os.path.exists(args.dados_brutos):
        sys.exit(f"Arquivo de dados brutos não encontrado: {args.dados_brutos}")
    if not os.path.exists(args.sugestao):
        sys.exit(f"Arquivo de sugestão não encontrado: {args.sugestao}")

    sugestao = carregar_json(args.sugestao)
    if args.tipo == "json":
        erros = validar_json(carregar_json(args.dados_brutos), sugestao)
    else:
        erros = validar_html(carregar_texto(args.dados_brutos), sugestao)

    if erros:
        print("Sugestão rejeitada:")
        for erro in erros:
            print(f"- {erro}")
        return 1

    print("Sugestão validada com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
