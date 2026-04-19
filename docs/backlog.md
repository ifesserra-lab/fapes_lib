# Backlog De Desenvolvimento

Backlog operacional do projeto `fapes_lib`.

Repositorio publico:

```text
https://github.com/ifesserra-lab/fapes_lib
```

## Como Usar Este Backlog

Este documento organiza as issues do GitHub por fase, prioridade e dependencia.

Regras de gestao:

- GitHub Issues e a fonte de verdade operacional.
- Este arquivo e o mapa de planejamento do projeto.
- Toda implementacao deve ter issue aberta antes do codigo.
- Toda implementacao deve seguir TDD estrito.
- Nenhum item de codigo deve comecar antes de existir comportamento documentado em EPIC/Gherkin quando aplicavel.
- Issues concluidas devem permanecer listadas para manter historico e rastreabilidade.
- Ao criar, fechar ou reordenar issues relevantes, atualizar este backlog.

## Status

| Status | Significado |
| --- | --- |
| `Done` | Issue concluida e fechada. |
| `Ready` | Issue aberta e pronta para iniciar. |
| `Blocked` | Issue depende de outra pendencia. |
| `Planned` | Item planejado, mas ainda sem issue aberta. |

## Prioridades

| Prioridade | Significado |
| --- | --- |
| `P0` | Fundacao obrigatoria para o projeto andar. |
| `P1` | Funcionalidade principal da biblioteca. |
| `P2` | Qualidade, automacao, documentacao ou melhoria importante. |
| `P3` | Evolucao futura. |

## Definition Of Ready

Uma issue esta pronta para desenvolvimento quando:

- possui objetivo claro;
- possui escopo e criterios de aceite;
- referencia EPIC/Gherkin quando aplicavel;
- nao exige credenciais reais no codigo;
- pode ser implementada com teste falhando primeiro;
- nao conflita com anti-patterns definidos em `.agents/AGENTS.MD`.

## Definition Of Done

Uma issue esta concluida quando:

- testes automatizados relevantes passam;
- comportamento publico esta documentado;
- nao ha senha, token ou credenciais versionadas;
- nao ha teste unitario dependente de rede real;
- o design respeita OO, MVC adaptado e separacao de responsabilidades;
- anti-patterns relevantes foram evitados;
- a issue foi fechada por commit, PR ou comentario de conclusao.

## Roadmap

```text
Fase 0: Planejamento documental
  -> Fase 1: Fundacao Python e configuracao
    -> Fase 2: Autenticacao e transporte HTTP
      -> Fase 3: Consultas diretas
        -> Fase 4: Extracao encadeada
          -> Fase 5: Exportacao
            -> Fase 6: BDD, CI e documentacao publica
```

## Fase 0: Planejamento Documental

| Issue | Prioridade | Status | Entrega |
| --- | --- | --- | --- |
| [#1](https://github.com/ifesserra-lab/fapes_lib/issues/1) | P0 | Done | `docs/architecture.md` |
| [#2](https://github.com/ifesserra-lab/fapes_lib/issues/2) | P0 | Done | `docs/epics/EPIC-001-autenticacao.md` |
| [#3](https://github.com/ifesserra-lab/fapes_lib/issues/3) | P0 | Done | `docs/epics/EPIC-002-consultas-api.md` |
| [#4](https://github.com/ifesserra-lab/fapes_lib/issues/4) | P0 | Done | `docs/epics/EPIC-003-extracao-dados.md` |
| [#5](https://github.com/ifesserra-lab/fapes_lib/issues/5) | P0 | Done | `docs/epics/EPIC-004-exportacao-dados.md` |
| [#6](https://github.com/ifesserra-lab/fapes_lib/issues/6) | P0 | Done | `docs/features/autenticacao.feature` |
| [#7](https://github.com/ifesserra-lab/fapes_lib/issues/7) | P0 | Done | `docs/features/consultas_api.feature` |
| [#8](https://github.com/ifesserra-lab/fapes_lib/issues/8) | P0 | Done | `docs/features/extracao_dados.feature` |
| [#9](https://github.com/ifesserra-lab/fapes_lib/issues/9) | P0 | Done | `docs/features/exportacao_dados.feature` |

## Fase 1: Fundacao Python

| Issue | Prioridade | Status | Dependencias | Resultado esperado |
| --- | --- | --- | --- | --- |
| [#10](https://github.com/ifesserra-lab/fapes_lib/issues/10) | P0 | Ready | #1 a #9 | Pacote Python inicial com `pyproject.toml`, layout `src/` e `tests/`. |
| [#11](https://github.com/ifesserra-lab/fapes_lib/issues/11) | P0 | Ready | #10 | `FapesSettings` carregando configuracao por ambiente com TDD. |
| [#12](https://github.com/ifesserra-lab/fapes_lib/issues/12) | P0 | Ready | #10 | Excecoes de dominio e mascaramento de segredos. |

Ordem recomendada:

1. #10
2. #11
3. #12

## Fase 2: Autenticacao E Transporte HTTP

| Issue | Prioridade | Status | Dependencias | Resultado esperado |
| --- | --- | --- | --- | --- |
| [#13](https://github.com/ifesserra-lab/fapes_lib/issues/13) | P0 | Blocked | #10, #12 | `FapesHttpClient` com `httpx`, timeout, JSON e erros encapsulados. |
| [#14](https://github.com/ifesserra-lab/fapes_lib/issues/14) | P0 | Blocked | #11, #12, #13 | `FapesAuthenticator` obtendo token JWT sem vazar segredo. |

Ordem recomendada:

1. #13
2. #14

## Fase 3: Consultas Diretas

| Issue | Prioridade | Status | Dependencias | Resultado esperado |
| --- | --- | --- | --- | --- |
| [#15](https://github.com/ifesserra-lab/fapes_lib/issues/15) | P1 | Blocked | #12, #13 | Parser/modelos tolerantes para envelope e resposta de `setores`. |
| [#16](https://github.com/ifesserra-lab/fapes_lib/issues/16) | P1 | Blocked | #14, #15 | `FapesApiClient` com metodos para todos os endpoints diretos. |

Ordem recomendada:

1. #15
2. #16

## Fase 4: Extracao Encadeada

| Issue | Prioridade | Status | Dependencias | Resultado esperado |
| --- | --- | --- | --- | --- |
| [#17](https://github.com/ifesserra-lab/fapes_lib/issues/17) | P1 | Blocked | #16 | `FapesExtractor` com fluxos compostos e metadados de execucao. |

## Fase 5: Exportacao

| Issue | Prioridade | Status | Dependencias | Resultado esperado |
| --- | --- | --- | --- | --- |
| [#18](https://github.com/ifesserra-lab/fapes_lib/issues/18) | P1 | Blocked | #17 | Exportadores JSON, JSONL e CSV na camada View. |

## Fase 6: BDD, CI E Documentacao Publica

| Issue | Prioridade | Status | Dependencias | Resultado esperado |
| --- | --- | --- | --- | --- |
| [#19](https://github.com/ifesserra-lab/fapes_lib/issues/19) | P2 | Blocked | #14, #16 | Features Gherkin conectadas a testes BDD sem rede por padrao. |
| [#20](https://github.com/ifesserra-lab/fapes_lib/issues/20) | P2 | Blocked | #10 | Pipeline de qualidade com testes, lint e type check. |
| [#21](https://github.com/ifesserra-lab/fapes_lib/issues/21) | P2 | Done | #1 a #9 | README raiz para uso publico do projeto. |
| [#22](https://github.com/ifesserra-lab/fapes_lib/issues/22) | P2 | Done | Nenhuma | Licenca MIT adicionada ao repositorio. |
| [#23](https://github.com/ifesserra-lab/fapes_lib/issues/23) | P2 | Done | Nenhuma | `release.md` com versoes e changelog. |

## Visao Kanban Atual

### Ready

- [#10](https://github.com/ifesserra-lab/fapes_lib/issues/10) CHORE: inicializar pacote Python com pyproject e layout src
- [#11](https://github.com/ifesserra-lab/fapes_lib/issues/11) TDD: implementar FapesSettings para configuracao via ambiente
- [#12](https://github.com/ifesserra-lab/fapes_lib/issues/12) TDD: implementar excecoes de dominio e mascaramento de segredos

### Blocked

- [#13](https://github.com/ifesserra-lab/fapes_lib/issues/13) TDD: implementar FapesHttpClient para transporte HTTP
- [#14](https://github.com/ifesserra-lab/fapes_lib/issues/14) TDD: implementar FapesAuthenticator para gerar token JWT
- [#15](https://github.com/ifesserra-lab/fapes_lib/issues/15) TDD: implementar modelos e parser do envelope de resposta
- [#16](https://github.com/ifesserra-lab/fapes_lib/issues/16) TDD: implementar FapesApiClient para consultas diretas
- [#17](https://github.com/ifesserra-lab/fapes_lib/issues/17) TDD: implementar FapesExtractor para extracao encadeada
- [#18](https://github.com/ifesserra-lab/fapes_lib/issues/18) TDD: implementar exportadores JSON, JSONL e CSV
- [#19](https://github.com/ifesserra-lab/fapes_lib/issues/19) TEST: conectar features Gherkin a testes BDD
- [#20](https://github.com/ifesserra-lab/fapes_lib/issues/20) CI: configurar pipeline de qualidade

### Done

- [#1](https://github.com/ifesserra-lab/fapes_lib/issues/1) DOC: criar `docs/architecture.md`
- [#2](https://github.com/ifesserra-lab/fapes_lib/issues/2) EPIC-001
- [#3](https://github.com/ifesserra-lab/fapes_lib/issues/3) EPIC-002
- [#4](https://github.com/ifesserra-lab/fapes_lib/issues/4) EPIC-003
- [#5](https://github.com/ifesserra-lab/fapes_lib/issues/5) EPIC-004
- [#6](https://github.com/ifesserra-lab/fapes_lib/issues/6) Feature de autenticacao
- [#7](https://github.com/ifesserra-lab/fapes_lib/issues/7) Feature de consultas
- [#8](https://github.com/ifesserra-lab/fapes_lib/issues/8) Feature de extracao
- [#9](https://github.com/ifesserra-lab/fapes_lib/issues/9) Feature de exportacao
- [#21](https://github.com/ifesserra-lab/fapes_lib/issues/21) README raiz publico
- [#22](https://github.com/ifesserra-lab/fapes_lib/issues/22) Licenca do projeto
- [#23](https://github.com/ifesserra-lab/fapes_lib/issues/23) Releases e changelog

## Proxima Acao Recomendada

Iniciar pela issue [#10](https://github.com/ifesserra-lab/fapes_lib/issues/10), criando a fundacao Python do pacote.

Depois seguir para:

1. [#11](https://github.com/ifesserra-lab/fapes_lib/issues/11)
2. [#12](https://github.com/ifesserra-lab/fapes_lib/issues/12)
3. [#13](https://github.com/ifesserra-lab/fapes_lib/issues/13)
4. [#14](https://github.com/ifesserra-lab/fapes_lib/issues/14)

## Regras De Atualizacao

Atualizar este arquivo quando:

- uma issue for criada;
- uma issue for fechada;
- uma dependencia mudar;
- uma prioridade mudar;
- um item `Blocked` ficar pronto;
- o escopo de uma fase mudar.

Ao fechar uma issue por commit, usar mensagem com referencia:

```text
Closes #NUMERO
```
