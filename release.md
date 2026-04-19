# Releases E Changelog

Historico de releases, versoes planejadas e changelog da biblioteca `fapes_lib`.

Repositorio:

```text
https://github.com/ifesserra-lab/fapes_lib
```

## Politica De Versionamento

O projeto seguira versionamento semantico:

```text
MAJOR.MINOR.PATCH
```

Regras:

- `MAJOR`: mudancas incompativeis na API publica.
- `MINOR`: novas funcionalidades compativeis com versoes anteriores.
- `PATCH`: correcoes, ajustes internos e melhorias sem mudanca funcional relevante.

Enquanto a lib estiver em `0.x`, a API publica ainda podera mudar entre releases menores.

## Status Atual

| Campo | Valor |
| --- | --- |
| Versao atual | `0.0.0` |
| Estado | Desenvolvimento inicial da biblioteca |
| Pacote Python | Inicializado com layout `src/` |
| Publicacao PyPI | Ainda nao publicada |
| API publica estavel | Ainda nao |

## Releases

### 0.0.0 - Bootstrap De Planejamento

Status: concluida como base documental do repositorio.

Data: 2026-04-19

Tipo: documentacao e governanca inicial.

Changelog:

- Criado repositorio publico `ifesserra-lab/fapes_lib`.
- Documentada a API FAPES `webServicesSig`.
- Documentado endpoint correto de autenticacao.
- Criado `.env` local e `.gitignore` para impedir versionamento de credenciais.
- Criado `.agents/AGENTS.MD` com regras obrigatorias do projeto.
- Definidas premissas de TDD, OO, MVC adaptado, EPICs e Gherkin.
- Criada arquitetura em `docs/architecture.md`.
- Criadas EPICs iniciais:
  - `EPIC-001-autenticacao`
  - `EPIC-002-consultas-api`
  - `EPIC-003-extracao-dados`
  - `EPIC-004-exportacao-dados`
- Criados cenarios Gherkin:
  - `autenticacao.feature`
  - `consultas_api.feature`
  - `extracao_dados.feature`
  - `exportacao_dados.feature`
- Criado backlog em `docs/backlog.md`.
- Criado README publico.
- Adicionada licenca MIT.

Observacoes:

- Esta versao nao contem codigo Python de producao.
- Esta versao nao deve ser publicada no PyPI.
- Esta versao serve como marco de governanca e planejamento.

### 0.1.0 - Fundacao Do Pacote Python

Status: implementada no codigo; ainda nao publicada/tagueada.

Issues relacionadas:

- [#10](https://github.com/ifesserra-lab/fapes_lib/issues/10)
- [#11](https://github.com/ifesserra-lab/fapes_lib/issues/11)
- [#12](https://github.com/ifesserra-lab/fapes_lib/issues/12)

Changelog previsto:

- Inicializar `pyproject.toml`.
- Criar layout `src/fapes_lib`.
- Criar estrutura `tests/`.
- Configurar ferramentas de qualidade.
- Implementar `FapesSettings` com TDD.
- Implementar excecoes de dominio.
- Implementar mascaramento de segredos.
- Garantir que testes unitarios nao dependem de rede.

Criterio de saida:

- `pytest` executa sem erro estrutural.
- Configuracao por ambiente tem cobertura de testes.
- Excecoes de dominio estao testadas.
- Nenhuma credencial real esta versionada.

### 0.2.0 - Autenticacao E Transporte HTTP

Status: parcialmente implementada; transporte HTTP concluido e autenticacao pendente.

Issues relacionadas:

- [#13](https://github.com/ifesserra-lab/fapes_lib/issues/13)
- [#14](https://github.com/ifesserra-lab/fapes_lib/issues/14)

Changelog previsto:

- Implementar `FapesHttpClient` usando `httpx`.
- Implementar timeout configuravel.
- Implementar envio de JSON.
- Tratar erros de rede com excecoes da biblioteca.
- Tratar respostas nao JSON.
- Implementar `FapesAuthenticator`.
- Autenticar em `https://servicos.fapes.es.gov.br/webServicesSig/auth.php`.
- Interpretar resposta real `{ "token": "..." }`.
- Tratar credenciais invalidas.
- Tratar resposta de autenticacao sem token.
- Evitar vazamento de senha e token em erros.

Criterio de saida:

- Autenticacao testada com mock HTTP.
- Nenhum teste unitario acessa a API real.
- Token fica encapsulado.
- Falhas de autenticacao usam excecoes de dominio.

### 0.3.0 - Consultas Diretas Da API

Status: planejada.

Issues relacionadas:

- [#15](https://github.com/ifesserra-lab/fapes_lib/issues/15)
- [#16](https://github.com/ifesserra-lab/fapes_lib/issues/16)

Changelog previsto:

- Implementar parser do envelope `data/encontrado/msg/erro/qtd`.
- Suportar resposta especial de `setores` sem envelope.
- Preservar campos extras em respostas da API.
- Implementar `FapesApiClient`.
- Disponibilizar metodos:
  - `listar_setores`
  - `listar_editais`
  - `listar_edital_chamadas`
  - `listar_edital_objetos_filhos`
  - `listar_projetos`
  - `listar_projeto_bolsas`
  - `listar_bolsistas`
  - `obter_pesquisador`
  - `listar_modalidade_bolsas`
  - `listar_situacao_projeto`

Criterio de saida:

- Todos os endpoints diretos possuem testes unitarios.
- Parametros obrigatorios sao validados antes da requisicao.
- Nao ha copy-paste desnecessario entre endpoints.

### 0.4.0 - Extracao Encadeada

Status: planejada.

Issue relacionada:

- [#17](https://github.com/ifesserra-lab/fapes_lib/issues/17)

Changelog previsto:

- Implementar `FapesExtractor`.
- Extrair cadastros auxiliares.
- Extrair editais com chamadas.
- Extrair editais com projetos.
- Extrair projetos com bolsas e bolsistas.
- Executar extracao completa.
- Retornar metadados de execucao.
- Reportar falhas por etapa sem sucesso silencioso.

Criterio de saida:

- Fluxos compostos testados com cliente fake/mock.
- Ordem de chamadas testada.
- Falhas encadeadas indicam etapa afetada.
- Nenhum token ou senha aparece em erros.

### 0.5.0 - Exportacao E BDD

Status: planejada.

Issues relacionadas:

- [#18](https://github.com/ifesserra-lab/fapes_lib/issues/18)
- [#19](https://github.com/ifesserra-lab/fapes_lib/issues/19)

Changelog previsto:

- Implementar exportador JSON.
- Implementar exportador JSONL.
- Implementar exportador CSV.
- Preservar metadados permitidos.
- Rejeitar CSV com dados aninhados sem normalizacao explicita.
- Conectar features Gherkin a testes BDD.
- Garantir que BDD roda sem rede por padrao.

Criterio de saida:

- Exportadores testados.
- Features principais conectadas a testes automatizados.
- Dados sensiveis nao aparecem em arquivos gerados.

### 0.6.0 - Qualidade E Automacao

Status: implementada antecipadamente; CI configurado antes das demais fases.

Issue relacionada:

- [#20](https://github.com/ifesserra-lab/fapes_lib/issues/20)

Changelog previsto:

- Configurar pipeline de CI.
- Rodar `pytest`.
- Rodar `ruff check`.
- Rodar `ruff format --check`.
- Rodar `mypy src` quando configurado.
- Garantir que testes de integracao real exigem opt-in.

Criterio de saida:

- CI passa em pull requests.
- `.env` nao e necessario no CI padrao.
- Testes reais contra API nao rodam por padrao.

### 1.0.0 - API Publica Estavel

Status: planejada.

Changelog previsto:

- Congelar API publica principal.
- Documentar instalacao e uso completo.
- Garantir cobertura adequada dos fluxos principais.
- Publicar release GitHub estavel.
- Avaliar publicacao em PyPI.

Criterio de saida:

- API publica documentada.
- Testes e CI verdes.
- Sem credenciais versionadas.
- Fluxos principais de autenticacao, consulta, extracao e exportacao funcionando.
- Politica de compatibilidade documentada.

## Modelo De Changelog Futuro

Cada nova release deve seguir este formato:

```markdown
### X.Y.Z - Titulo Da Release

Status: planejada | em desenvolvimento | publicada

Data: YYYY-MM-DD

Issues relacionadas:

- #NUMERO

Changelog:

- Adicionado: ...
- Alterado: ...
- Corrigido: ...
- Removido: ...

Notas de migracao:

- ...
```

## Regras De Release

- Toda release deve ter issue ou milestone associada.
- Toda release deve atualizar este arquivo.
- Mudancas publicas devem atualizar README e docs quando necessario.
- Releases publicadas devem ser tagueadas no Git.
- Releases nao devem conter `.env`, senha, token JWT ou credenciais reais.
