"""Persistência dos resultados em CSV e JSON."""

import csv
import json
import os
from typing import List

from . import config
from .models import Noticia
from .utils import logger


def salvar_csv(registros: List[Noticia], caminho: str) -> None:
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=config.COLUNAS_SAIDA)
        escritor.writeheader()
        for registro in registros:
            escritor.writerow(registro.to_dict())
    logger.info("CSV salvo em %s (%d linhas).", caminho, len(registros))


def salvar_json(registros: List[Noticia], caminho: str) -> None:
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(
            [r.to_dict() for r in registros],
            arquivo,
            ensure_ascii=False,
            indent=2,
        )
    logger.info("JSON salvo em %s (%d registros).", caminho, len(registros))
