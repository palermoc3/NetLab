# Proposta: uso de LLM no diagnóstico e manutenção da coleta

Esta proposta descreve como um modelo de linguagem (LLM) apoiaria — sem
substituir — o processo de diagnóstico, manutenção e monitoramento da
rotina de coleta. A integração com uma API de LLM não foi implementada,
mas o gate de validação offline foi: `scripts/validar_sugestao_llm.py`
valida sugestões estruturadas antes que elas sejam aceitas.

## 1. Onde o LLM entraria

| Etapa | Função do modelo |
|---|---|
| **Diagnóstico inicial** (quando a coleta quebra) | Analisar uma amostra do HTML/API bruto + a configuração atual e **sugerir** seletores ou mapeamentos de campos. |
| **Manutenção periódica** | Comparar a estrutura HTML/API em duas datas diferentes e sinalizar mudanças relevantes. |
| **Monitoramento contínuo** | Ler os logs de execução (`coleta.log`) e o relatório de qualidade (`docs/relatorio_qualidade.md`) e gerar um resumo em linguagem natural de anomalias (ex.: "completude caiu de 95% para 40% na execução de hoje"), para triagem humana mais rápida. |
| **Apoio a testes** | A partir de um HTML de exemplo, sugerir casos de teste adicionais (campos ausentes, cards atípicos) para `tests/test_scraper.py`. |

O LLM **nunca** grava diretamente em produção nem decide sozinho trocar
seletores ou mapeamentos. Ele só propõe, e a proposta passa por validação
automática + revisão humana.

## 2. Que dados seriam fornecidos ao modelo

- Um **trecho truncado e anonimizado** do HTML ou JSON bruto.
- A configuração atual da coleta (`SEARCH_API_URL`, headers e campos
  mapeados), para o modelo explicar a diferença.
- Trechos do `coleta.log` (nível WARNING/ERROR) da execução recente.
- O relatório de qualidade (`docs/relatorio_qualidade.md`) das últimas
  execuções, para dar contexto de tendência (não só um snapshot).
- **Nunca** seriam enviados: dados pessoais de terceiros, credenciais, ou
  o HTML completo sem necessidade (minimização de dados).

## 3. Como as respostas do modelo seriam validadas antes de entrar na rotina

O ponto crítico é impedir que o modelo "alucine" um seletor, caminho JSON
ou dado que não existe na resposta bruta. Fluxo implementado:

```text
1. Modelo recebe HTML/API de amostra + configuração atual.
2. Modelo é instruído a responder SOMENTE em JSON estruturado, ex.:
   {
     "fonte": "api",
     "campos": {
       "titulo": "result.hits.hits[]._source.title",
       "resumo": "result.hits.hits[]._source.caption",
       "data_publicacao": "result.hits.hits[]._source.issued",
       "url": "result.hits.hits[]._source.url"
     },
     "justificativa": "..."
   }
3. VALIDAÇÃO PROGRAMÁTICA (automática, sem confiar "de olho" no modelo):
   a. Para JSON, conferir que todos os caminhos sugeridos existem e
      retornam valores úteis nos dados brutos.
   b. Para HTML, rodar `BeautifulSoup(html).select(...)` de verdade e
      rejeitar seletores inválidos ou sem correspondência.
4. Se passou na validação automática: rodar o candidato contra a
   amostra de referência (dados/amostra_referencia.csv) e calcular as
   mesmas métricas de scripts/avaliar_qualidade.py.
5. Só então um humano revisa o diff em `src/config.py` (pull request) e
   aprova — o merge nunca é automático.
```

Comando de validação implementado:

```bash
python scripts/validar_sugestao_llm.py \
  --tipo json \
  --dados-brutos tests/fixtures/api_busca_exemplo.json \
  --sugestao docs/sugestao_llm_exemplo.json
```

## 4. Mecanismos contra alucinação / dados inventados

- **Grounding obrigatório**: seletores ou caminhos JSON sugeridos precisam
  existir nos dados brutos fornecidos.
- **Saída estruturada e restrita**: o prompt exige JSON com um schema
  fixo; respostas fora do schema são rejeitadas antes mesmo de tentar
  interpretar o conteúdo.
- **Nunca perguntar "qual é o seletor certo?" sem contexto** — o modelo
  sempre recebe o HTML real como entrada; nunca é usado para "lembrar de
  cor" a estrutura de um site (isso é justamente o tipo de erro que causou
  o bug original, e um LLM sem grounding cometeria o mesmo erro).
- **Amostra de referência como gate de qualidade**: mesmo que a sugestão
  seja sintaticamente válida, ela só é promovida se as métricas de
  `avaliar_qualidade.py` contra `amostra_referencia.csv` melhorarem ou se
  mantiverem em relação à execução anterior.
- **Revisão humana final**: a mudança em `src/config.py` é sempre uma PR
  revisável, nunca um `git commit` automático do agente.
