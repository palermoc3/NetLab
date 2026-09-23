# Coleta G1 — busca por "LGPD"

Solução em Python para corrigir a coleta de resultados da busca do G1 em
`https://g1.globo.com/busca/?q=lgpd`, usando Beautiful Soup no diagnóstico
da página e na extração/fallback HTML, com coleta principal pela API
headless atualmente usada pelo front-end do G1.

## Diagnóstico

Em 2026-09-12, `scripts/diagnostico.py` mostrou que a página real:

- responde `HTTP 200`;
- não contém `lgpd` no HTML bruto;
- não contém `<article>` nem cards de resultado;
- contém apenas o shell React e o componente `backstage-cms-all-search-results`;
- usa `POST https://busca.globo.com/v1/search` para carregar os resultados.

Portanto, a causa principal do problema deixou de ser apenas seletor CSS:
os resultados não estão mais no HTML inicial. O scraper antigo podia
executar sem erro e voltar vazio porque `BeautifulSoup(...).select(...)`
não encontrava cards.

Problemas adicionais corrigidos:


- seletores fixos e frágeis;
- ausência de tratamento para campos nulos;
- falta de timeout, retries e tratamento HTTP;
- paginação fixa sem parada por páginas vazias;
- ausência de deduplicação;
- falta de logs e rastreabilidade.

## Roadmap Executado

1. Diagnosticar a página real do G1.
2. Confirmar que os resultados não aparecem no HTML inicial.
3. Descobrir a API usada pelo front-end.
4. Implementar coleta via API, mantendo fallback HTML com Beautiful Soup.
5. Normalizar URLs de tracking da Globo (`measures.globo.com?...&u=...`).
6. Tratar falhas de rede, HTTP inválido, JSON inválido e campos ausentes.
7. Deduplicar por URL normalizada.
8. Gerar CSV/JSON, testes e relatório de qualidade.
9. Documentar instalação, execução, limitações e estratégia de LLM.

## Estrutura

```text
src/
  config.py        # constantes, API, seletores de fallback
  scraper.py       # coleta via API + fallback HTML
  models.py        # dataclass Noticia
  storage.py       # CSV/JSON
  utils.py         # logs, retry, extração segura
scripts/
  diagnostico.py        # diagnóstico da página real
  run_scraper.py        # CLI de coleta
  avaliar_qualidade.py  # métricas vs. amostra de referência
  validar_sugestao_llm.py
dados/
  g1_resultado.csv
  g1_resultado.json
  amostra_referencia.csv
docs/
  proposta_llm.md
  relatorio_qualidade.md
  roadmap_futuro.md
  sugestao_llm_exemplo.json
tests/
```

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

Diagnóstico:

```bash
python scripts/diagnostico.py --termo lgpd --pagina 1
```

Coleta:

```bash
python scripts/run_scraper.py --termo lgpd --paginas 5 \
  --saida-csv dados/g1_resultado.csv \
  --saida-json dados/g1_resultado.json
```

Testes:

```bash
python -m pytest tests -q
```

Avaliação de qualidade:

```bash
python scripts/avaliar_qualidade.py \
  --coletado dados/g1_resultado.csv \
  --referencia dados/amostra_referencia.csv \
  --saida docs/relatorio_qualidade.md
```

## Resultado Obtido

Coleta real disponível em `dados/g1_resultado.csv` e reavaliada em 2026-09-12:

- 5 páginas;
- até 10 resultados por página;
- 49 registros únicos;
- saída em `dados/g1_resultado.csv` e `dados/g1_resultado.json`;
- logs em console e `coleta.log`.

Testes automatizados:

```text
17 passed
```

Métricas geradas em `docs/relatorio_qualidade.md`:

- completude: 100%;
- unicidade: 100%;
- consistência: 100%;
- rastreabilidade: 100%;
- cobertura da amostra de referência: 100%;
- acurácia média de título/resumo: 100%.

## Dados Coletados

Cada registro salvo contém:

- `id`: hash estável da URL normalizada;
- `titulo`;
- `url`;
- `resumo`;
- `data_publicacao`;
- `pagina`;
- `coletado_em`;
- `seletor_usado` ou fonte usada (`api:busca.globo.com/v1/search`).

Registros sem `titulo` ou `url` são descartados. Campos opcionais ausentes
são preservados como vazios e contabilizados nas métricas de completude.

## Estratégia de LLM

A proposta está em `docs/proposta_llm.md`. O projeto inclui um validador
offline em `scripts/validar_sugestao_llm.py`, que checa sugestões
estruturadas de LLM contra HTML/JSON bruto antes de qualquer alteração no
scraper.

Mecanismos anti-alucinação:

- o modelo só recebe dados reais coletados;
- respostas estruturadas em JSON;
- seletores ou caminhos JSON sugeridos precisam existir nos dados brutos;
- mudanças entram via revisão, não por automação cega.

## Limitações e Melhorias

- A API do G1 é pública e usada pelo front-end, mas não é um contrato
  formal de estabilidade; mudanças de payload podem exigir ajuste.
- `robots.txt` deve ser revisitado antes de uso operacional contínuo.
- A rotina acessa apenas resultados publicamente disponíveis, respeita
  delays entre requisições e não contorna autenticação, paywall, captcha
  ou restrição de acesso. Antes de uso operacional contínuo, recomenda-se
  revisar `robots.txt` e as políticas de uso do portal.
- A amostra de referência é pequena, adequada ao exercício; em produção,
  deve ser ampliada e versionada por data de coleta.
- O projeto não está inicializado como repositório Git neste diretório
  (`git status` retornou “not a git repository”); para entrega final,
  inicialize/publicar em Git conforme solicitado pelo processo seletivo.
- Melhorias futuras: alerta automático para queda de completude,
  comparação diária de HTML/API, respeito a `Retry-After`, métricas por
  página e suporte a parâmetros de ordenação/filtro.

Os próximos passos recomendados estão detalhados em `docs/roadmap_futuro.md`.
