# 🌌 ImpactTrace

> **Análise de Impacto de Código Instantânea e Mapeamento Arquitetural para Desenvolvedores e Agentes de IA.**

---

## 📌 O Problema e a Solução

### 💥 O Problema ("Efeito Borboleta no Código")

Em sistemas em crescimento, uma alteração aparentemente inofensiva em um arquivo de base (como uma tabela de banco em `database.py` ou um modelo em `models.py`) pode quebrar silenciosamente endpoints e validadores em camadas superiores. Rastrear manualmente *"quem depende de quem"* exige tempo e memória cognitiva.

### 🛡️ A Solução

O **ImpactTrace** analisa a estrutura do seu projeto em milissegundos via **AST (Abstract Syntax Tree)** sem executar o seu código. Ele constrói um **Grafo Dirigido de Dependências** e usa o **`git diff`** para calcular exatamente quais arquivos sofrerão impacto direto e indireto antes mesmo do seu próximo `git commit`.

---

## 🏗️ Arquitetura e Estrutura do Módulo

Uma das maiores vantagens de engenharia do ImpactTrace é a sua **modularidade**. Você **não** precisa clonar nem copiar todo o repositório de desenvolvimento do ImpactTrace para o seu projeto pessoal.

Basta copiar a pasta `impact/` para a raiz do seu projeto existente:

```text
seu-projeto-pessoal/
├── impact/                <-- Apenas esta pasta precisa ser copiada!
│   ├── __init__.py
│   ├── ast_parser.py      # Extração de AST e Hashes SHA-256
│   ├── browser.py         # Launch e fallback de navegadores
│   ├── cli.py             # Ponto de entrada CLI (Typer)
│   ├── config.py          # Gerenciamento de workspace e .impact/
│   ├── git_service.py     # Leitura do git diff / status
│   ├── graph_engine.py    # Algoritmos de busca em grafos (NetworkX)
│   └── visualizer.py      # Renderizador Rich (Terminal) e Pyvis (HTML)
├── .impact/               # Gerado automaticamente (cache local e reports)
├── database.py
├── models.py
├── endpoints.py
└── requirements.txt

```

---

## ⚖️ Trade-offs de Engenharia: Design e Performance

Ao projetar o ImpactTrace, tomamos decisões conscientes sobre onde investir tempo e recursos:

| Aspecto | Decisão de Design | Trade-off Assumido |
| --- | --- | --- |
| **Instalação das Bibliotecas** | Uso de dependências como `pyvis`, `networkx`, `rich` e `gitpython`. | **A Instalação Inicial Demora Razoavelmente:** O download e compilação dessas bibliotecas no `pip install` leva alguns segundos a mais. |
| **Visualização no Navegador** | Geração de HTML5 interativo via VisNetwork. | **A Recompensa:** Gráficos ricos, arrastáveis, com zoom e alternância de layout (Hierárquico vs Força-Dirigida) que eliminam qualquer dúvida sobre a arquitetura. |
| **Execução do Scan e Análise** | Parser AST com cache incremental via SHA-256 e poda no nível do S.O. | **Velocidade Ultra-Rápida ($O(N)$):** O escaneamento e o cálculo de impacto rodam em **poucos milissegundos**, mesmo em projetos com centenas de arquivos. |

---

## 🚀 Guia de Instalação e Execução

### 1. Copie o Módulo e Instale as Dependências

No seu projeto pessoal, adicione as dependências do ImpactTrace ao seu ambiente virtual (`venv`):

```bash
pip install typer rich networkx pyvis gitpython

```

*(Ou adicione as linhas acima ao seu `requirements.txt` e rode `pip install -r requirements.txt`).*

### 2. Inicialize o ImpactTrace no Seu Projeto

Dentro da pasta do seu projeto pessoal, execute:

```bash
python impact/cli.py init

```

> *Isso criará o diretório local `.impact/` com as regras de exclusão padrão (`venv`, `.git`, etc).*

### 3. Mapeie as Dependências (Scan)

Para construir o primeiro grafo de dependências do projeto:

```bash
python impact/cli.py scan

```

Você verá um diagnóstico imediato dos arquivos analisados e a quantidade de relações encontradas.

---

## 🎮 Comandos do Dia a Dia

### 🔍 Analisar Impactos de Alterações do Git (`analyze`)

Altere um ou mais arquivos no seu código e rode:

```bash
python impact/cli.py analyze

```

O terminal exibirá uma árvore colorida dividida em:

* ✏️ **Arquivos Alterados:** O que você modificou no Git.
* 💥 **Impacto Direto:** Quem importa seus arquivos diretamente.
* 🌊 **Impacto Indireto:** Efeito cascata em outras camadas da aplicação.

#### 🌐 Abrindo o Relatório Interativo no Navegador:

```bash
python impact/cli.py analyze --web

```

#### 🤖 Exportando para Agentes de IA (Cursor, Copilot, ChatGPT):

```bash
python impact/cli.py analyze --format ai-json

```

> *Gera uma estrutura JSON limpa projetada para servir de contexto exato para LLMs entenderem o impacto do seu refactoring.*

---

### 🌌 Visualizar o Grafo Arquitetural Completo (`graph`)

Para ver a estrutura completa de todas as conexões do seu projeto em uma interface HTML5 no seu navegador padrão:

```bash
python impact/cli.py graph

```

* **Legenda Visual:**
* 🔵 **Azul (Raiz):** Entrypoints / Views (Top da hierarquia).
* 🟣 **Roxo (Intermediário):** Serviços, Validadores e Regras de Negócio.
* 🟢 **Verde (Folha):** Módulos utilitários e conexões de Banco de Dados.



---

## 🗺️ Roadmap de Evolução Futura

Atualmente, o ImpactTrace funciona com mapeamento na granularidade de **arquivos** (`File-Level Dependencies`). A visão de futuro do projeto inclui:

```text
[ Versão Atual 1.0 ] ➔ Mapeamento de Dependências entre Arquivos (.py)
        │
        ▼
[ Versão 2.0 (Em Breve) ] ➔ Análise Fina de Símbolos Internos
                          ├── Rastreamento de Funções Chamas
                          ├── Inspecção de Importação de Variáveis e Classes
                          └── Identificação do Escopo Exato da Quebra

```

> 💡 **Nota do Desenvolvedor:** A ideia é evoluir a análise AST para entender exatamente qual **função** ou **variável** dentro do arquivo causará a quebra, *sem que precisemos construir um compilador completo... ou quase isso! 😉*

---

## 📄 Licença

Este projeto é distribuído sob a licença **MIT**. Sinta-se livre para adaptar e utilizar no seu fluxo de trabalho diário.