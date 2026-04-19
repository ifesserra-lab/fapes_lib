# EPIC-003: Extracao Encadeada De Dados

## Status

Planejada.

## Objetivo

Orquestrar fluxos de extracao que combinam multiplos endpoints da API FAPES de forma previsivel, testavel e sem misturar responsabilidades.

## Escopo

Inclui:

- extrair cadastros auxiliares;
- extrair editais com chamadas;
- extrair editais com projetos;
- extrair projetos com bolsas e bolsistas;
- executar extracao completa;
- retornar metadados sobre a execucao.

Nao inclui:

- persistencia em banco de dados;
- paralelismo na primeira versao;
- retry automatico avancado;
- enriquecimento externo de dados.

## Dependencias

- Arquitetura: issue #1.
- Autenticacao: EPIC-001.
- Consultas: EPIC-002.
- Feature BDD: `docs/features/extracao_dados.feature`.

## User Stories

### US-014: Extrair Cadastros Auxiliares

Como consumidor da biblioteca, quero extrair setores, modalidades de bolsas e situacoes de projeto, para usar esses dados como referencia nas demais extracoes.

Criterios de aceite:

- O fluxo deve consultar `setores`, `modalidade_bolsas` e `situacao_projeto`.
- O resultado deve identificar a origem de cada conjunto.
- Falhas devem informar qual consulta falhou.

### US-015: Extrair Editais Com Chamadas

Como consumidor da biblioteca, quero extrair editais com suas chamadas, para analisar periodos de submissao.

Criterios de aceite:

- O fluxo deve consultar `editais`.
- Para cada edital com identificador, deve consultar `edital_chamadas`.
- O resultado deve preservar editais mesmo quando nao houver chamadas.

### US-016: Extrair Editais Com Projetos

Como consumidor da biblioteca, quero extrair editais com seus projetos, para analisar projetos vinculados a cada edital.

Criterios de aceite:

- O fluxo deve consultar `projetos` para cada edital.
- A ausencia de projetos deve ser representada explicitamente.
- Erros por edital devem ser rastreaveis.

### US-017: Extrair Projetos Com Bolsas E Bolsistas

Como consumidor da biblioteca, quero extrair bolsas e bolsistas de cada projeto, para analisar execucao de bolsas.

Criterios de aceite:

- O fluxo deve consultar `projeto_bolsas` e `bolsistas`.
- Cada resultado deve manter relacao com `codprj`.
- Falhas em uma consulta devem ser reportadas sem desaparecer silenciosamente.

### US-018: Executar Extracao Completa

Como consumidor da biblioteca, quero executar uma extracao completa, para obter uma visao integrada dos dados FAPES.

Criterios de aceite:

- A ordem de extracao deve ser previsivel.
- O resultado deve conter dados e metadados da execucao.
- O fluxo deve permitir teste unitario com cliente mockado.
- O fluxo nao deve depender de rede em testes unitarios.

## Estrategia De Testes

Seguir TDD:

- testar fluxo com cliente fake;
- testar ordem de chamadas;
- testar resultado parcial sem dados;
- testar falha em consulta encadeada;
- testar metadados da extracao;
- testar que token e senha nao aparecem em erros.

## Riscos

- Volume de dados alto.
- API lenta ou indisponivel.
- Algumas relacoes podem depender de campos inconsistentes.
- `edital_objetos_filhos` ainda nao tem schema detalhado.

## Anti-Patterns Evitados

- God Object concentrando todos os fluxos.
- Spaghetti code na orquestracao.
- Falha silenciosa em consulta encadeada.
- Testes de unidade chamando API real.

## Rastreabilidade

- Feature: `docs/features/extracao_dados.feature`.
- Arquitetura: `docs/architecture.md`.
- Issue: #4.
