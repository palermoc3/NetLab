#!/usr/bin/env python3
"""Avalia a coleta contra uma amostra de referência."""

import argparse
import csv
import difflib
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit


def normalizar_url(url: str) -> str:
    if not url:
        return ""
    partes = urlsplit(url.strip())
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", "")).rstrip("/")


def carregar_csv(caminho: str) -> list:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def similaridade(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


REGEX_URL = re.compile(r"^https?://")
CAMPOS_ESSENCIAIS = ["titulo", "resumo", "data_publicacao", "url"]


def avaliar(coletados: list, referencia: list) -> dict:
    total = len(coletados)
    relatorio = {"total_coletado": total, "total_referencia": len(referencia)}

    completos = [r for r in coletados if all((r.get(c) or "").strip() for c in CAMPOS_ESSENCIAIS)]
    relatorio["completude_pct"] = round(100 * len(completos) / total, 1) if total else 0.0

    urls = [normalizar_url(r.get("url", "")) for r in coletados if r.get("url")]
    unicas = set(urls)
    duplicatas = len(urls) - len(unicas)
    relatorio["unicidade_pct"] = round(100 * len(unicas) / len(urls), 1) if urls else 0.0
    relatorio["duplicatas_encontradas"] = duplicatas

    consistentes = 0
    for r in coletados:
        url_ok = bool(REGEX_URL.match(r.get("url") or ""))
        data_ok = bool((r.get("data_publicacao") or "").strip())
        pagina_ok = str(r.get("pagina") or "").isdigit()
        if url_ok and data_ok and pagina_ok:
            consistentes += 1
    relatorio["consistencia_pct"] = round(100 * consistentes / total, 1) if total else 0.0

    rastreaveis = [
        r for r in coletados
        if (r.get("pagina") or "").strip() and (r.get("coletado_em") or "").strip()
    ]
    relatorio["rastreabilidade_pct"] = round(100 * len(rastreaveis) / total, 1) if total else 0.0

    coletados_por_url = {normalizar_url(r.get("url", "")): r for r in coletados}
    encontrados = 0
    similaridades_titulo = []
    similaridades_resumo = []
    for ref in referencia:
        url_ref = normalizar_url(ref.get("url", ""))
        correspondente = coletados_por_url.get(url_ref)
        if correspondente:
            encontrados += 1
            similaridades_titulo.append(similaridade(ref.get("titulo", ""), correspondente.get("titulo", "")))
            similaridades_resumo.append(similaridade(ref.get("resumo", ""), correspondente.get("resumo", "")))

    relatorio["cobertura_referencia_pct"] = (
        round(100 * encontrados / len(referencia), 1) if referencia else None
    )
    relatorio["acuracia_titulo_media_pct"] = (
        round(100 * sum(similaridades_titulo) / len(similaridades_titulo), 1) if similaridades_titulo else None
    )
    relatorio["acuracia_resumo_media_pct"] = (
        round(100 * sum(similaridades_resumo) / len(similaridades_resumo), 1) if similaridades_resumo else None
    )

    timestamps = [r.get("coletado_em") for r in coletados if r.get("coletado_em")]
    if timestamps:
        try:
            mais_recente = max(datetime.fromisoformat(t) for t in timestamps)
            relatorio["coleta_mais_recente"] = mais_recente.isoformat(timespec="seconds")
        except ValueError:
            relatorio["coleta_mais_recente"] = None
    else:
        relatorio["coleta_mais_recente"] = None

    return relatorio


def formatar_relatorio_md(r: dict) -> str:
    linhas = [
        "# Relatório de qualidade da coleta\n",
        f"- Total de registros coletados: **{r['total_coletado']}**",
        f"- Total de itens na amostra de referência: **{r['total_referencia']}**\n",
        "| Dimensão | Métrica | Valor |",
        "|---|---|---|",
        f"| Completude | % registros com todos os campos essenciais | {r['completude_pct']}% |",
        f"| Unicidade | % de URLs únicas | {r['unicidade_pct']}% ({r['duplicatas_encontradas']} duplicata(s)) |",
        f"| Consistência | % registros com formato válido (url/data/página) | {r['consistencia_pct']}% |",
        f"| Rastreabilidade | % registros com página + timestamp de coleta | {r['rastreabilidade_pct']}% |",
        f"| Acurácia (cobertura) | % da amostra de referência encontrada na coleta | {r['cobertura_referencia_pct']}% |",
        f"| Acurácia (título) | similaridade textual média com a referência | {r['acuracia_titulo_media_pct']}% |",
        f"| Acurácia (resumo) | similaridade textual média com a referência | {r['acuracia_resumo_media_pct']}% |",
        f"| Atualidade | timestamp da coleta mais recente | {r['coleta_mais_recente']} |",
    ]
    return "\n".join(linhas) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Avalia qualidade da coleta vs. amostra de referência.")
    parser.add_argument("--coletado", required=True)
    parser.add_argument("--referencia", required=True)
    parser.add_argument("--saida", default="docs/relatorio_qualidade.md")
    args = parser.parse_args()

    if not os.path.exists(args.coletado):
        sys.exit(f"Arquivo de dados coletados não encontrado: {args.coletado}")
    if not os.path.exists(args.referencia):
        sys.exit(f"Arquivo de referência não encontrado: {args.referencia}")

    coletados = carregar_csv(args.coletado)
    referencia = carregar_csv(args.referencia)
    resultado = avaliar(coletados, referencia)
    md = formatar_relatorio_md(resultado)

    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(md)

    print(md)
    print(f"\nRelatório também salvo em {args.saida}")


if __name__ == "__main__":
    main()
