import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.validar_sugestao_llm import validar_json


FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "api_busca_exemplo.json")


def carregar_fixture():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_valida_mapeamento_json_existente():
    sugestao = {
        "campos": {
            "titulo": "result.hits.hits[]._source.title",
            "resumo": "result.hits.hits[]._source.caption",
            "data_publicacao": "result.hits.hits[]._source.issued",
            "url": "result.hits.hits[]._source.url",
        }
    }

    assert validar_json(carregar_fixture(), sugestao) == []


def test_rejeita_mapeamento_json_inexistente():
    sugestao = {"campos": {"titulo": "result.hits.hits[]._source.campo_inventado"}}

    erros = validar_json(carregar_fixture(), sugestao)

    assert erros
    assert "campo_inventado" in erros[0]
