# Testes BDD

Este projeto usa `pytest-bdd` para conectar os arquivos `.feature` em Gherkin aos testes automatizados Python.

## Decisao

A ferramenta escolhida foi `pytest-bdd`.

Motivos:

- integra diretamente com `pytest`, que ja e usado na suite do projeto;
- permite reaproveitar fixtures, fakes e asserts Python;
- executa cenarios documentados em `docs/features/`;
- mantem a suite BDD no mesmo comando de qualidade: `python -m pytest`.

## Regra De Rede

Os testes BDD rodam sem rede por padrao.

Steps BDD devem usar fakes, mocks ou fixtures locais. Chamadas reais para a API FAPES pertencem somente a testes de integracao opcionais, protegidos por variavel explicita como `FAPES_RUN_INTEGRATION=1`.

## Regra De Segredos

Steps BDD nao devem imprimir credenciais, senha, token JWT ou payloads sensiveis.

Quando um cenario precisar validar autenticacao, ele deve usar valores ficticios e verificar que `repr`, `str`, exceptions e mensagens publicas nao exibem o token completo.

## Papel Na Estrategia De Testes

BDD nao substitui TDD unitario.

Uso recomendado:

- testes unitarios continuam cobrindo regras, erros e edge cases;
- BDD cobre cenarios principais escritos em linguagem de negocio;
- cada novo fluxo relevante deve ter primeiro uma User Story ou cenario Gherkin, quando aplicavel;
- os steps devem chamar a API publica da biblioteca, nao detalhes internos desnecessarios.

## Cenario Inicial Conectado

O primeiro cenario conectado e:

```text
docs/features/autenticacao.feature
  Cenario: Autenticacao com sucesso
```

Ele usa um cliente HTTP fake, retorna um token ficticio e confirma que a autenticacao fica em memoria sem expor o token completo em mensagens publicas.
