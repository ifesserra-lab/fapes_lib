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

## Cenarios Conectados

Os cenarios conectados ate aqui sao:

```text
docs/features/autenticacao.feature
  Cenario: Autenticacao com sucesso

docs/features/extracao_dados.feature
  Cenario: Extrair cadastros auxiliares
  Cenario: Extrair editais com chamadas
  Cenario: Extrair editais com projetos
  Cenario: Extrair projetos com bolsas e bolsistas
  Cenario: Executar extracao completa em ordem previsivel
  Cenario: Falha em consulta encadeada
  Cenario: Extracao sem dados encontrados
```

Eles usam clientes fake, nao dependem de rede real e validam que tokens ou senhas
ficticias nao aparecem em mensagens publicas de erro.
