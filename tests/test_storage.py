import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import Noticia
from src.storage import salvar_csv, salvar_json


def _registro_exemplo():
    return Noticia(
        titulo="Título de teste sobre LGPD",
        resumo="Resumo de teste",
        data_publicacao="2026-08-10T09:00:00-03:00",
        url="https://g1.globo.com/noticia/exemplo.ghtml",
        pagina=1,
        coletado_em=datetime(2026, 9, 12, 10, 0, 0),
        seletor_usado="teste",
    )


def test_salvar_csv_gera_arquivo_com_cabecalho_e_linha(tmp_path):
    caminho = tmp_path / "saida.csv"
    salvar_csv([_registro_exemplo()], str(caminho))

    with open(caminho, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    assert len(linhas) == 1
    assert linhas[0]["titulo"] == "Título de teste sobre LGPD"
    assert linhas[0]["url"] == "https://g1.globo.com/noticia/exemplo.ghtml"


def test_salvar_json_gera_lista_valida(tmp_path):
    caminho = tmp_path / "saida.json"
    salvar_json([_registro_exemplo()], str(caminho))

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)

    assert isinstance(dados, list)
    assert len(dados) == 1
    assert dados[0]["pagina"] == 1
    assert "id" in dados[0]
