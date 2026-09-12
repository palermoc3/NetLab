#!/usr/bin/env python3
"""CLI da coleta G1."""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import config
from src.scraper import G1BuscaScraper
from src.storage import salvar_csv, salvar_json
from src.utils import configurar_logging


def main():
    parser = argparse.ArgumentParser(description="Coleta resultados de busca do G1.")
    parser.add_argument("--termo", default=config.TERMO_BUSCA_PADRAO, help="Termo de busca (padrão: lgpd)")
    parser.add_argument("--paginas", type=int, default=config.TOTAL_PAGINAS_PADRAO, help="Número máximo de páginas")
    parser.add_argument("--saida-csv", default="dados/g1_resultado.csv", help="Caminho do CSV de saída")
    parser.add_argument("--saida-json", default="dados/g1_resultado.json", help="Caminho do JSON de saída")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    configurar_logging(args.log_level)

    scraper = G1BuscaScraper(termo_busca=args.termo)
    registros = scraper.coletar(total_paginas=args.paginas)

    salvar_csv(registros, args.saida_csv)
    salvar_json(registros, args.saida_json)

    print(f"\nConcluído: {len(registros)} registro(s) salvos em {args.saida_csv} e {args.saida_json}")


if __name__ == "__main__":
    main()
