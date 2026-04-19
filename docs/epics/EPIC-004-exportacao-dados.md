# EPIC-004: Exportacao De Dados Extraidos

## Status

Planejada.

## Objetivo

Disponibilizar uma camada de saida para salvar dados extraidos pela biblioteca em formatos simples e interoperaveis.

## Escopo

Inclui exportacao para:

- JSON;
- JSONL;
- CSV.

Inclui tambem preservacao de metadados basicos da extracao.

Nao inclui:

- Parquet na primeira versao;
- banco de dados;
- dashboards;
- upload automatico para storage externo.

## Dependencias

- Arquitetura: issue #1.
- Extracao: EPIC-003.
- Feature BDD: `docs/features/exportacao_dados.feature`.

## User Stories

### US-019: Exportar JSON

Como consumidor da biblioteca, quero exportar dados extraidos em JSON, para preservar estrutura aninhada de editais, projetos, bolsas e bolsistas.

Criterios de aceite:

- O exportador deve escrever JSON valido.
- Deve preservar objetos aninhados.
- Deve permitir incluir metadados da extracao.

### US-020: Exportar JSONL

Como consumidor da biblioteca, quero exportar registros em JSONL, para processar grandes volumes linha a linha.

Criterios de aceite:

- Cada linha deve ser um JSON valido.
- O exportador deve aceitar iteravel de registros.
- Falhas de escrita devem gerar erro claro.

### US-021: Exportar CSV

Como consumidor da biblioteca, quero exportar dados tabulares em CSV, para abrir resultados em ferramentas de planilha ou ETL.

Criterios de aceite:

- O exportador deve escrever cabecalho.
- Deve aceitar lista de dicionarios planos.
- Deve falhar de forma clara quando dados aninhados exigirem normalizacao previa.

### US-022: Preservar Metadados Da Extracao

Como consumidor da biblioteca, quero preservar metadados da extracao, para auditar origem, horario e parametros usados.

Criterios de aceite:

- Metadados devem incluir fonte, data/hora de execucao e funcoes consultadas.
- Metadados nao devem conter senha ou token.
- Exportadores devem documentar como lidam com metadados.

## Estrategia De Testes

Seguir TDD:

- testar JSON valido;
- testar JSONL com uma linha por registro;
- testar CSV com cabecalho;
- testar erro de destino invalido;
- testar que metadados nao contem credenciais.

## Riscos

- CSV nao representa dados aninhados sem normalizacao.
- Arquivos grandes podem exigir streaming no futuro.
- Metadados podem vazar informacao sensivel se nao forem filtrados.

## Anti-Patterns Evitados

- Misturar exportacao com consulta HTTP.
- Fazer exportador conhecer token ou autenticador.
- Silent failure em erro de escrita.
- Normalizacao implicita que perde dados.

## Rastreabilidade

- Feature: `docs/features/exportacao_dados.feature`.
- Arquitetura: `docs/architecture.md`.
- Issue: #5.
