# yaddd
Yet another DDD for Python

## Terms and definitions
First, read [Domain Driven Thesaurus](https://github.com/pyDDD/yaddd/wiki/Thesaurus)


## Installation
You can choose any modern one dependencies manager like a:
`uv sync` or `poetry install` (only poetry >= 2.0)

Remember that in library mode you can choose optional dependencies for `yaddd` wich enable integration with third-part libraries:
1. `yaddd[pydantic]` — supports Pydnatic validators for `ValueObject`
2. `yaddd[sqlalchemy]` — supports type decorators in `ValueObject`
