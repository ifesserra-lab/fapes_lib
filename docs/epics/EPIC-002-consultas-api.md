# EPIC-002: Consultas Da API FAPES

## Status

Planejada.

## Objetivo

Disponibilizar metodos de consulta para todos os endpoints documentados da API FAPES `webServicesSig`.

## Escopo

Inclui consultas para:

- setores;
- editais;
- chamadas de edital;
- objetos filhos de edital;
- projetos por edital;
- bolsas por projeto;
- bolsistas por projeto;
- pesquisador;
- modalidades de bolsas;
- situacoes de projeto.

Nao inclui:

- extracao encadeada de multiplos endpoints;
- exportacao de dados;
- persistencia em banco;
- inferencia de campos nao documentados sem resposta real.

## Dependencias

- Arquitetura: issue #1.
- Autenticacao: EPIC-001.
- Feature BDD: `docs/features/consultas_api.feature`.
- Documentacao da API: `docs/api.md`.

## User Stories

### US-005: Listar Setores

Como consumidor da biblioteca, quero listar setores da FAPES, para obter gerencias e nucleos disponiveis.

Criterios de aceite:

- A consulta deve usar `funcao` igual a `setores`.
- A resposta sem envelope deve ser aceita conforme documentacao atual.
- Erros HTTP devem ser tratados com excecao da biblioteca.

### US-006: Listar Editais

Como consumidor da biblioteca, quero listar editais, para descobrir oportunidades cadastradas no SIG/FAPES.

Criterios de aceite:

- A consulta deve usar `funcao` igual a `editais`.
- A resposta deve aceitar envelope `data/encontrado/msg/erro/qtd`.
- Cada item deve preservar campos desconhecidos quando existirem.

### US-007: Listar Chamadas De Edital

Como consumidor da biblioteca, quero listar chamadas de um edital, para conhecer janelas de submissao.

Criterios de aceite:

- A consulta deve exigir `codedt`.
- A ausencia de `codedt` deve gerar erro de validacao.
- A resposta deve preservar datas como string inicialmente.

### US-008: Listar Projetos Por Edital

Como consumidor da biblioteca, quero listar projetos vinculados a um edital, para analisar execucao e coordenadores.

Criterios de aceite:

- A consulta deve exigir `codedt`.
- A resposta deve aceitar campos de projeto, situacao, coordenador e termo.
- Valores financeiros devem ser tratados como decimal ou tipo numerico apropriado.

### US-009: Listar Bolsas Por Projeto

Como consumidor da biblioteca, quero listar bolsas de um projeto, para avaliar cotas, duracao e valores.

Criterios de aceite:

- A consulta deve exigir `codprj`.
- A resposta deve manter campos de orcamento, cotas, valor total, nome e sigla.

### US-010: Listar Bolsistas Por Projeto

Como consumidor da biblioteca, quero listar bolsistas de um projeto, para acompanhar bolsas concedidas e pagamentos.

Criterios de aceite:

- A consulta deve exigir `codprj`.
- A resposta deve aceitar `folhas_pagamentos` como lista.
- Campos bancarios devem ser tratados como sensiveis na documentacao e exportacao futura.

### US-011: Obter Pesquisador

Como consumidor da biblioteca, quero obter dados de pesquisador, para relacionar pesquisadores a projetos e bolsas.

Criterios de aceite:

- A consulta deve exigir `codpes`.
- Tipos documentados incorretamente pelo Swagger devem ser tratados de forma tolerante.
- Campos desconhecidos devem ser preservados.

### US-012: Listar Modalidades De Bolsas

Como consumidor da biblioteca, quero listar modalidades de bolsas e niveis, para manter cadastro auxiliar atualizado.

Criterios de aceite:

- A consulta deve usar `funcao` igual a `modalidade_bolsas`.
- A resposta deve aceitar niveis aninhados.
- Status `0/1` deve ser interpretado sem quebrar se vier como boolean ou inteiro.

### US-013: Listar Situacoes De Projeto

Como consumidor da biblioteca, quero listar situacoes de projeto, para interpretar status de projetos retornados.

Criterios de aceite:

- A consulta deve usar `funcao` igual a `situacao_projeto`.
- A resposta deve preservar `situacao_id`, `situacao_descricao` e `situacao_status`.

## Estrategia De Testes

Seguir TDD para cada endpoint:

- teste de payload enviado;
- teste de resposta com envelope;
- teste de erro HTTP;
- teste de parametro obrigatorio ausente;
- teste de resposta com campos extras.

## Riscos

- Inconsistencias de tipos no Swagger.
- Endpoint `edital_objetos_filhos` sem schema detalhado.
- Resposta de `setores` diferente do envelope comum.

## Anti-Patterns Evitados

- Copy-paste entre metodos de endpoint.
- Magic strings espalhadas.
- Parsing rigido demais para uma API inconsistente.
- Expor payload bruto como unico contrato publico.

## Rastreabilidade

- Feature: `docs/features/consultas_api.feature`.
- Arquitetura: `docs/architecture.md`.
- Issue: #3.
