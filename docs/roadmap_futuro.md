# Roadmap Futuro

Próximas tarefas recomendadas para manter e evoluir a coleta G1 depois da correção atual.

## Manutenção Da Coleta

1. Versionar snapshots pequenos da resposta da API e do HTML de diagnóstico.
2. Criar alerta quando a coleta retornar zero registros ou menos que o mínimo esperado.
3. Criar alerta quando completude, unicidade ou rastreabilidade ficarem abaixo de 95%.
4. Registrar mudanças de payload da API em um changelog técnico.
5. Validar periodicamente `robots.txt` e limites operacionais de acesso.

## Qualidade Dos Dados

1. Ampliar `dados/amostra_referencia.csv` para 10 a 20 itens por execução de referência.
2. Criar amostras por data de coleta para comparar estabilidade ao longo do tempo.
3. Adicionar métricas por página coletada.
4. Separar itens editoriais, publicidade e outros tipos de resultado quando esse campo estiver disponível.
5. Normalizar datas para um formato único em UTC.

## Testes

1. Adicionar fixtures com payloads parciais: sem resumo, sem data, sem URL e JSON inválido.
2. Testar paginação com múltiplas páginas de resposta da API.
3. Testar fallback HTML apenas como caminho secundário.
4. Adicionar teste para headers exigidos pela API.

## Operação

1. Inicializar/publicar o projeto em Git.
2. Criar job agendado para coleta recorrente.
3. Salvar logs por execução, com data no nome do arquivo.
4. Manter histórico de CSV/JSON por data, sem sobrescrever coletas anteriores.
5. Criar relatório comparativo entre execuções.

## Uso De LLM

1. Usar LLM para comparar snapshots de HTML/API e apontar mudanças estruturais.
2. Validar toda sugestão do modelo contra dados brutos antes de aceitar.
3. Usar a LLM apenas para triagem e geração de hipóteses, nunca para criar dados coletados.
