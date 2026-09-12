"""Utilitários do scraper."""

import functools
import logging
import random
import time
from typing import Callable, Optional

import requests
from bs4.element import Tag


def configurar_logging(nivel: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("g1_scraper")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, nivel.upper(), logging.INFO))

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S")
    )
    logger.addHandler(console)

    try:
        arquivo = logging.FileHandler("coleta.log", encoding="utf-8")
        arquivo.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
        )
        logger.addHandler(arquivo)
    except OSError:
        pass

    return logger


logger = configurar_logging()


def retry_com_backoff(max_tentativas: int, base_segundos: float):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ultima_excecao: Optional[Exception] = None
            for tentativa in range(1, max_tentativas + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.ConnectionError, requests.Timeout) as e:
                    ultima_excecao = e
                    espera = base_segundos * (2 ** (tentativa - 1)) + random.uniform(0, 1)
                    logger.warning(
                        "Falha de conexão (tentativa %d/%d): %s. Aguardando %.1fs.",
                        tentativa, max_tentativas, e, espera,
                    )
                    time.sleep(espera)
                except requests.HTTPError as e:
                    status = e.response.status_code if e.response is not None else None
                    if status and 500 <= status < 600:
                        ultima_excecao = e
                        espera = base_segundos * (2 ** (tentativa - 1))
                        logger.warning(
                            "Erro HTTP %s (tentativa %d/%d). Aguardando %.1fs.",
                            status, tentativa, max_tentativas, espera,
                        )
                        time.sleep(espera)
                    else:
                        logger.error("Erro HTTP não recuperável: %s", e)
                        raise
            logger.error("Esgotadas %d tentativas. Desistindo desta requisição.", max_tentativas)
            if ultima_excecao:
                raise ultima_excecao
        return wrapper
    return decorator


def texto_seguro(tag: Optional[Tag]) -> Optional[str]:
    if tag is None:
        return None
    texto = tag.get_text(strip=True)
    return texto or None


def atributo_seguro(tag: Optional[Tag], nome: str) -> Optional[str]:
    if tag is None:
        return None
    valor = tag.get(nome)
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    return valor or None
