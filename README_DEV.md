# 🚀 Especificação de Arquitetura: Project ImpactTrace (`.impact`)

> **Visão Geral:** O **ImpactTrace** é uma ferramenta leve de Análise de Impacto de Mudanças (*Change Impact Analysis*) projetada para desenvolvedores e agentes de IA. Seu objetivo é mapear as conexões de um sistema e responder instantaneamente à pergunta: *"Se eu alterar este arquivo, o que mais no projeto pode quebrar?"*.

---

## 🎯 1. O Problema & A Solução

* **O Problema:** Alterações "simples" em um arquivo frequentemente geram efeitos colaterais em cascata em outras partes do sistema, exigindo esforço manual para rastrear todas as dependências afetadas.
* **A Solução:** Um motor híbrido local que analisa o código via **AST (Abstract Syntax Tree)**, constrói um **Grafo Dirigido de Dependências** e usa o **`git diff`** para calcular o impacto exato antes do `git commit`.

---

## 🛡️ 2. Princípios de Design

1. **Leve e Local:** Nenhum dado de código sai da máquina do desenvolvedor.
2. **Performance Instantânea:** Uso do Git para analisar apenas os arquivos modificados na sessão de trabalho, evitando reprocessar o projeto inteiro.
3. **Multi-Interface:** Suporte a exibição rápida via Terminal (CLI) e visualização interativa via Browser (Web UI).
4. **AI-Ready:** Saídas estruturadas em JSON projetadas para servirem de contexto direto para Agentes de IA (Cursor, Copilot, Aider).

---

## 🏗️ 3. Arquitetura e Módulos do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                      CLI / ENGINE                       │
│  (impact init | impact scan | impact analyze | --web)   │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
            ▼                         ▼
┌───────────────────────┐ ┌───────────────────────────────┐
│     Git Integration   │ │        AST Parser Engine      │
│  (Detecta arquivos    │ │  (Extrai imports / módulos    │
│   modificados no diff)│ │   via 'ast' e 'tree-sitter')  │
└───────────┬───────────┘ └───────────┬───────────────────┘
            │                         │
            └───────────┬─────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  NetworkX Graph Engine                  │
│       (Monta e calcula busca no Grafo Dirigido)         │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
            ▼                         ▼
┌───────────────────────┐ ┌───────────────────────────────┐
│      Terminal UI      │ │         Web UI Visual         │
│  (Árvore via 'rich')  │ │  (HTML Interativo via Pyvis)  │
└───────────────────────┘ └───────────────────────────────┘

```

---

## 🔄 4. Modelo Híbrido de Execução

### Fase 1: Escaneamento e Mapeamento Global (`impact scan`)

* Executado periodicamente ou na inicialização do projeto.
* Varre os arquivos do projeto (ignorando padrões como `venv/`, `.git/`, `__pycache__`).
* Gera a árvore AST de cada arquivo e identifica os `imports`/dependências.
* Salva o Grafo de Dependências no banco local `.impact/cache.db` (SQLite) ou `.impact/graph.json`.

### Fase 2: Análise Incremental Pré-Commit (`impact analyze`)

1. O desenvolvedor altera um ou mais arquivos.
2. O sistema executa internamente: `git status` ou `git diff --name-only`.
3. O algoritmo pega apenas os arquivos alterados e realiza uma busca **Downstream** (o que este arquivo afeta) e **Upstream** (quem depende deste arquivo) no grafo armazenado em `.impact/`.
4. Retorna a lista e o grafo de impacto em milissegundos.

---

## 💻 5. Stack Tecnológica

| Componente | Tecnologia Escolhida | Justificativa |
| --- | --- | --- |
| **Linguagem Base** | Python 3.10+ | Ecossistema maduro para AST, CLI e análise de grafos. |
| **Parser AST** | Módulo `ast` nativo + `tree-sitter` | O `ast` cobre Python na PoC; `tree-sitter` garantirá suporte poliglota no futuro. |
| **Engine do Grafo** | `NetworkX` | Padrão da indústria em Python para criação e navegação em grafos. |
| **Integração Git** | `GitPython` / `subprocess` | Leitura nativa e rápida de repositórios Git. |
| **Interface Terminal** | `Rich` + `Typer` | Criação de CLIs modernas com tabelas, cores e visualização em árvore. |
| **Interface Web** | `Pyvis` / `HTML5` | Gera grafos interativos (zoom, arrastar, clicar) em HTML sem necessidade de servidor complexo. |

---

## 📁 6. Estrutura da Pasta Local `.impact/`

Cada repositório utilizando a ferramenta possuirá uma pasta oculta na raiz:

```text
meu-projeto/
├── .gitignore
├── .impact/               <-- Gerado pelo 'impact init'
│   ├── config.json        <-- Padrões de include/exclude
│   ├── cache.json         <-- Cache do Grafo de Dependências
│   └── report.html        <-- Relatório gráfico gerado para o browser
├── src/
│   ├── main.py
│   └── service.py

```

### Exemplo do arquivo `.impact/config.json`:

```json
{
  "version": "1.0",
  "ignore_patterns": [
    "venv/*",
    ".git/*",
    "__pycache__/*",
    "tests/*"
  ],
  "default_mode": "cli",
  "max_depth": 3
}

```

---

## 🛠️ 7. Interface de Linha de Comando (CLI)

```bash
# Inicializa a pasta .impact/ e a configuração no projeto
$ impact init

# Mapeia todo o projeto e atualiza o grafo local
$ impact scan

# Analisa automaticamente as alterações não commitadas (via Git Diff)
$ impact analyze

# Analisa o impacto de um arquivo específico
$ impact analyze --file src/services/user_service.py

# Analisa e abre o grafo interativo no navegador
$ impact analyze --web

# Exporta o contexto do impacto formatado para Agentes de IA
$ impact analyze --format=ai-json

```

---

## 🗺️ 8. Roadmap de Evolução

```text
[ PoC - Versão 1.0 ]
 └── Mapeamento a Nível de Arquivos (File Dependencies)
 └── Leitura de AST em Python
 └── Análise via Git Diff
 └── CLI com Árvore Visual (Rich) e Grafo HTML (Pyvis)

[ Versão 2.0 - Símbolos & Precisão ]
 └── Mapeamento a Nível de Funções e Classes
 └── Redução drástica de falsos positivos
 └── Parser de SQL / Migrações do Banco de Dados

[ Versão 3.0 - Integração com IA ]
 └── Plugin para Git Hooks (`pre-commit`)
 └── Injeção automática de contexto no Cursor/Copilot/Aider
 └── Suporte Multi-Linguagem via Tree-sitter (JS/TS, C#, Go)

```