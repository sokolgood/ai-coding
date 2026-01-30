# AI Coding Agent

Автоматизированная система для разработки кода на основе GitHub Issues с использованием LLM. Система включает три основных агента: **Code Agent** (реализация задач), **Review Agent** (код-ревью) и **Fix Agent** (исправление по замечаниям).

## 🚀 Быстрый старт

### Запуск через Docker

Система поставляется как Docker-образ и запускается через CLI.

#### 1. Pull образа

```bash
docker pull ghcr.io/sokolgood/ai-coding-agent:latest
```

#### 2. Запуск Code Agent (создание/обновление PR из Issue)

```bash
docker run --rm \
  -e GH_TOKEN=$GH_TOKEN \
  -e LLM_API_KEY=$LLM_API_KEY \
  -e LLM_BASE_URL=$LLM_BASE_URL \
  -e LLM_MODEL_NAME=gpt-4o-mini \
  -e LANGFUSE_SECRET_KEY=$LANGFUSE_SECRET_KEY \
  -e LANGFUSE_PUBLIC_KEY=$LANGFUSE_PUBLIC_KEY \
  -e LANGFUSE_BASE_URL=$LANGFUSE_BASE_URL \
  -e REPO=owner/repo \
  -e REPO_PATH=/repo \
  -v "$(pwd):/repo" \
  ghcr.io/sokolgood/ai-coding-agent:latest \
  code \
    --issue 42 \
    --base main \
    --max-iter 5
```

#### 3. Запуск Review Agent (ревью PR)

```bash
docker run --rm \
  -e GH_TOKEN=$GH_TOKEN \
  -e LLM_API_KEY=$LLM_API_KEY \
  -e LLM_BASE_URL=$LLM_BASE_URL \
  -e LLM_MODEL_NAME=gpt-4o-mini \
  -e LANGFUSE_SECRET_KEY=$LANGFUSE_SECRET_KEY \
  -e LANGFUSE_PUBLIC_KEY=$LANGFUSE_PUBLIC_KEY \
  -e LANGFUSE_BASE_URL=$LANGFUSE_BASE_URL \
  -e REPO=owner/repo \
  -e REPO_PATH=/repo \
  -e CI_CONCLUSION=success \
  -v "$(pwd):/repo" \
  ghcr.io/sokolgood/ai-coding-agent:latest \
  review \
    --pr 123
```

#### 4. Запуск Fix Agent (исправление по замечаниям)

```bash
docker run --rm \
  -e GH_TOKEN=$GH_TOKEN \
  -e LLM_API_KEY=$LLM_API_KEY \
  -e LLM_BASE_URL=$LLM_BASE_URL \
  -e LLM_MODEL_NAME=gpt-4o-mini \
  -e LANGFUSE_SECRET_KEY=$LANGFUSE_SECRET_KEY \
  -e LANGFUSE_PUBLIC_KEY=$LANGFUSE_PUBLIC_KEY \
  -e LANGFUSE_BASE_URL=$LANGFUSE_BASE_URL \
  -e REPO=owner/repo \
  -e REPO_PATH=/repo \
  -v "$(pwd):/repo" \
  ghcr.io/sokolgood/ai-coding-agent:latest \
  fix \
    --pr 123
```

### Переменные окружения

| Переменная | Описание | Обязательная |
|-----------|----------|--------------|
| `GH_TOKEN` | GitHub Personal Access Token | ✅ Да |
| `REPO` | Репозиторий в формате `owner/repo` | ✅ Да |
| `LLM_API_KEY` | API ключ для LLM (OpenAI) | Нет |
| `LLM_BASE_URL` | Базовый URL для LLM API (для прокси) | Нет |
| `LLM_MODEL_NAME` | Название модели (по умолчанию: `gpt-4o-mini`) | Нет |
| `REPO_PATH` | Путь к репозиторию в контейнере (по умолчанию: `/repo`) | Нет |
| `CI_CONCLUSION` | Результат CI/CD для Review Agent (`success`, `failure`, `cancelled`, `neutral`) | Нет |
| `LANGFUSE_SECRET_KEY` | Secret key для Langfuse observability | Нет |
| `LANGFUSE_PUBLIC_KEY` | Public key для Langfuse observability | Нет |
| `LANGFUSE_BASE_URL` | Base URL для Langfuse (по умолчанию: `https://cloud.langfuse.com`) | Нет |

### Пример GitHub Actions Workflow

```yaml
name: "Code Agent on Issue Opened"

on:
  issues:
    types: [opened]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  code:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Pull agent image
        run: docker pull ghcr.io/sokolgood/ai-coding-agent:latest

      - name: Run Code Agent
        env:
          GH_TOKEN: ${{ secrets.BOT_TOKEN }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_BASE_URL: ${{ secrets.LLM_BASE_URL }}
          LLM_MODEL_NAME: gpt-4o-mini
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_BASE_URL: ${{ secrets.LANGFUSE_BASE_URL }}
          REPO: ${{ github.repository }}
        run: |
          docker run --rm \
            -e GH_TOKEN \
            -e LLM_API_KEY \
            -e LLM_BASE_URL \
            -e LLM_MODEL_NAME \
            -e LANGFUSE_SECRET_KEY \
            -e LANGFUSE_PUBLIC_KEY \
            -e LANGFUSE_BASE_URL \
            -e REPO \
            -e REPO_PATH=/repo \
            -v "${{ github.workspace }}:/repo" \
            ghcr.io/sokolgood/ai-coding-agent:latest \
            code \
              --issue ${{ github.event.issue.number }} \
              --base main \
              --max-iter 5
```

## 📁 Структура проекта

```
ai-coding/
├── src/
│   ├── application/          # Application слой (оркестрация)
│   │   ├── code.py          # CodeWorker - обработка issues
│   │   ├── review.py        # ReviewWorker - ревью PR
│   │   └── fix.py           # FixWorker - исправление по замечаниям
│   │
│   ├── cli.py               # CLI интерфейс
│   ├── config.py            # Конфигурация (Settings)
│   │
│   ├── services/
│   │   ├── git/             # Git операции
│   │   │   ├── github.py    # GitHub API (GitProvider)
│   │   │   ├── ops.py       # Локальные git команды
│   │   │   └── auth.py      # Аутентификация (не используется)
│   │   │
│   │   ├── llm/             # LLM сервисы
│   │   │   ├── engine.py    # LLM клиент (OpenAI)
│   │   │   ├── factory.py   # Фабрики для LLM и промптов
│   │   │   │
│   │   │   ├── agents/      # AI агенты
│   │   │   │   ├── coder.py         # CoderAgent
│   │   │   │   ├── reviewer.py      # ReviewerAgent
│   │   │   │   └── sgr/             # Schema-Guided Reasoning
│   │   │   │       ├── coder.py     # SGRCoderAgent
│   │   │   │       └── reviewer.py  # SGRReviewerAgent
│   │   │   │
│   │   │   └── tools/       # Инструменты для агентов
│   │   │       ├── base.py
│   │   │       ├── update_file.py   # Обновление файлов
│   │   │       ├── create_file.py   # Создание файлов
│   │   │       ├── read_file.py
│   │   │       ├── list_directory.py
│   │   │       ├── grep_search.py
│   │   │       └── run_command.py   # (отключен)
│   │   │
│   │   └── repo/
│   │       └── context_builder.py   # Построение RepoContext
│   │
│   ├── types/               # Типы данных
│   │   ├── context.py      # CoderContext, ReviewerContext, RepoContext
│   │   ├── review.py       # ReviewReport
│   │   ├── coder_result.py # CoderResult
│   │   ├── sgr_plan.py     # SGRPlan
│   │   └── git_provider.py # GitProvider интерфейс
│   │
│   └── prompts/
│       ├── prompts.yaml    # Jinja2 шаблоны промптов
│       └── registry.py     # Регистр промптов
│
├── docker/
│   └── Dockerfile          # Multi-stage Dockerfile
│
└── pyproject.toml          # Зависимости (Poetry)
```

## 🏗️ Архитектура

### Application слой

Application слой (`src/application/`) отвечает за оркестрацию работы агентов и интеграцию с GitHub.

#### CodeWorker (`code.py`)

Обрабатывает GitHub Issues и создает/обновляет Pull Requests.

**Поток работы:**

1. Получает Issue из GitHub
2. Создает/переключается на ветку `agent/issue-{number}`
3. Проверяет существующий PR и определяет итерацию
4. Запускает `CoderAgent` для реализации задачи
5. Коммитит и пушит изменения
6. Создает/обновляет PR с метаданными итерации

**Ключевые особенности:**
- Отслеживание итераций через `IterationState` в теле PR
- Защита от бесконечных циклов (максимум итераций)
- Автоматическое управление ветками и PR

#### ReviewWorker (`review.py`)

Выполняет код-ревью Pull Request.

**Поток работы:**

1. Получает PR из GitHub
2. Извлекает diff и CI результаты
3. Строит контекст репозитория
4. Запускает `ReviewerAgent`
5. Парсит структурированный `ReviewReport`
6. Комментирует PR и управляет лейблами (`agent:approved` / `agent:fix`)

**Ключевые особенности:**
- Интеграция с CI/CD результатами
- Структурированный вывод через Pydantic модели
- Автоматическое управление лейблами

#### FixWorker (`fix.py`)

Исправляет код по замечаниям из Review.

**Поток работы:**

1. Получает PR и извлекает `IterationState`
2. Парсит последний review комментарий с `ReviewReport`
3. Форматирует feedback и передает в `CoderAgent`
4. Коммитит и пушит исправления
5. Обновляет итерацию в PR

**Ключевые особенности:**
- Использует `CoderAgent` для исправлений
- Парсит JSON из скрытых комментариев в PR
- Инкрементирует итерацию

### Schema-Guided Reasoning (SGR)

**Schema-Guided Reasoning** — двухфазный подход к выполнению задач:

1. **Планирование** (`SGRCoderAgent` / `SGRReviewerAgent`): Генерирует структурированный план выполнения
2. **Выполнение** (`CoderAgent` / `ReviewerAgent`): Выполняет план пошагово

#### SGR Plan структура

```python
class SGRPlan(BaseModel):
    role: Literal["coder", "reviewer"]
    objective: str
    assumptions: list[str]
    steps: list[SGRStep]
    risks: list[str]
    stop_conditions: list[str]

class SGRStep(BaseModel):
    id: str
    goal: str
    suggested_tools: list[ToolHint]
    done_criteria: list[str]
```

#### Пример SGR плана

```json
{
  "role": "coder",
  "objective": "Implement logging in the main file and add logging at service startup",
  "assumptions": [
    "The main file is located in src/main.py",
    "Logging library is already available"
  ],
  "steps": [
    {
      "id": "step_1",
      "goal": "Identify the main file for the application",
      "suggested_tools": [{"name": "list_directory", "purpose": "Explore project structure"}],
      "done_criteria": ["Main file location identified"]
    },
    {
      "id": "step_2",
      "goal": "Review existing code to determine best place to add logging",
      "suggested_tools": [{"name": "read_file", "purpose": "Read main file content"}],
      "done_criteria": ["Code structure understood"]
    },
    {
      "id": "step_3",
      "goal": "Modify main file to configure logging and add startup logs",
      "suggested_tools": [{"name": "update_file", "purpose": "Update file with logging"}],
      "done_criteria": ["Logging configured and startup logs added"]
    }
  ],
  "risks": ["Breaking existing functionality"],
  "stop_conditions": ["Logging successfully implemented"]
}
```

#### Преимущества SGR

- **Структурированность**: План формализован через Pydantic модели
- **Прозрачность**: Видно, что агент планирует делать
- **Надежность**: План валидируется перед выполнением
- **Отладка**: Легко понять, на каком шаге произошла ошибка

### Промпты

Промпты хранятся в `src/prompts/prompts.yaml` и используют Jinja2 для шаблонизации.

#### SGR Coder промпт

```yaml
sgr_coder:
  system: |-
    You are a Schema Guided Reasoning (SGR) agent that creates execution plans for coding tasks.

    Your job is to analyze a coding task and create a structured plan with ordered steps.

    PROJECT CONTEXT:
    {{ repo_context }}

    AVAILABLE TOOLS:
    {{ tools }}

    Rules:
    1. Use ONLY the tools provided in the tools list above
    2. Create 3-5 steps maximum
    3. Each step must have: goal, suggested tools, done criteria
    4. Steps should be sequential and logical
    5. No "magic commands" - only use available tools
    6. Be specific about file paths, search patterns, etc.
    7. Consider repository structure and conventions from PROJECT CONTEXT
    8. DO NOT plan steps for running tests, linters, or build commands - these are handled by CI/CD
    9. Focus only on code implementation steps (read files, modify files, create files)

    Output a structured plan that can be executed step by step.

  user: |-
    TASK CONTEXT:
    {{ task_context }}

    Create a detailed execution plan for implementing this task.
```

#### Coder промпт

```yaml
coder:
  system: |-
    You are an AI coding agent that implements features and fixes bugs.

    You have a pre-generated execution plan. Follow it step by step using the available tools.

    PROJECT CONTEXT:
    {{ repo_context }}

    Available tools:
    - list_directory: Explore project structure
    - read_file: Read file contents
    - update_file: Update an existing file with new content - STRONGLY PREFERRED for all file modifications.
      CRITICAL: You MUST read the file first using read_file, then provide the COMPLETE new file content (not a diff).
      Include ALL code in new_content - do NOT omit unchanged parts. The tool will automatically generate and apply the diff.
    - create_file: Create a new file (path, content) - use ONLY for creating completely new files that do not exist yet
    - grep_search: Search for patterns (query, include_pattern, exclude_pattern, case_sensitive)

    Guidelines:
    1. Follow the plan step by step
    2. ALWAYS read files using read_file tool before modifying them
    3. Use update_file for all file modifications - read the file first, then provide the COMPLETE new file content (not a diff or patch)
    4. CRITICAL: When using update_file, new_content must contain the ENTIRE file including all unchanged code. Do NOT omit unchanged parts.
    5. CRITICAL: Make MINIMAL changes - only modify what is necessary for the task. Do NOT:
       - Refactor functions that are not related to the task
       - Change function signatures/contracts unless explicitly required
       - Rewrite code that works correctly and is not part of the task
       - Add unnecessary improvements or "cleanup" that wasn't requested
       - Change formatting, style, or structure of unrelated code
    6. When providing full file content, preserve existing code exactly as-is except for the specific changes needed
    7. Use create_file only for creating completely new files that do not exist yet
    8. If update_file returns an error, read the file again to see the current state, then provide corrected new_content
    9. Follow existing code style and repository conventions from PROJECT CONTEXT
    10. If AGENTS.md is provided in PROJECT CONTEXT, treat it as authoritative repository rules
    11. NOTE: Runtime checks (linting/tests) are handled by CI/CD, not by the agent. Focus on implementing the task correctly.
    12. If review feedback is provided in the task, address all requested changes from the review

  user: |-
    TASK:
    {{ issue_description }}

    EXECUTION PLAN:
    ```json
    {{ sgr_plan_json }}
    ```
```

### Инструменты (Tools)

Агенты имеют доступ к следующим инструментам:

#### 1. `list_directory`
Список файлов и директорий в указанном пути.

```python
await tool.run(path="src")
# Returns: "DIR src/    0 bytes\nFILE main.py    1234 bytes"
```

#### 2. `read_file`
Чтение содержимого файла.

```python
await tool.run(path="src/main.py")
# Returns: полное содержимое файла
```

#### 3. `update_file` ⭐ (Основной инструмент)
Обновление существующего файла. **Ключевая особенность**: принимает **полный новый контент файла**, а не diff.

```python
await tool.run(
    path="src/main.py",
    new_content="import logging\n\nlogging.basicConfig(...)\n\n# ... весь файл целиком ..."
)
```

**Как это работает:**
1. LLM читает файл через `read_file`
2. LLM генерирует полный новый контент файла
3. `update_file` генерирует diff через `difflib.unified_diff`
4. Применяет изменения атомарно (через временный файл)
5. Валидирует Python синтаксис (для `.py` файлов)
6. Откатывает изменения при ошибке синтаксиса

**Почему это надежно:**
- LLM не генерирует diff (это сложно и часто ошибочно)
- Diff генерируется программно (всегда правильный формат)
- Атомарная запись (нет частично примененных изменений)
- Валидация синтаксиса перед сохранением

#### 4. `create_file`
Создание нового файла. Используется только для файлов, которых еще не существует.

```python
await tool.run(
    path="src/new_module.py",
    content="def hello():\n    print('Hello')\n"
)
```

#### 5. `grep_search`
Поиск паттернов в файлах репозитория.

```python
await tool.run(
    pattern="def.*main",
    path="src",
    recursive=True
)
```

#### 6. `apply_patch` (резервный)
Применение unified diff патча. Используется редко, так как `update_file` предпочтительнее.

#### 7. `run_command` (отключен)
Запуск shell команд. **Отключен** — проверки (linting/tests) выполняются в CI/CD, а не агентом.

## 🔄 Пайплайн работы

### Полный цикл: Issue → Code → Review → Fix

```
┌─────────────┐
│ GitHub Issue│
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Code Agent     │
│  (SGR Planning) │
└──────┬──────────┘
       │
       ├─► SGRCoderAgent: генерирует план
       │
       ├─► CoderAgent: выполняет план
       │   ├─► read_file
       │   ├─► update_file
       │   └─► create_file
       │
       ▼
┌─────────────────┐
│  Pull Request   │
│  (iteration=1)  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Review Agent    │
│ (SGR Planning)  │
└──────┬──────────┘
       │
       ├─► SGRReviewerAgent: генерирует план ревью
       │
       ├─► ReviewerAgent: выполняет ревью
       │   ├─► read_file (измененные файлы)
       │   ├─► grep_search (поиск паттернов)
       │   └─► генерирует ReviewReport
       │
       ▼
┌─────────────────┐
│ Review Comment  │
│ verdict: FAIL   │
│ + лейбл:fix     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Fix Agent      │
│  (использует    │
│   CoderAgent)   │
└──────┬──────────┘
       │
       ├─► Парсит ReviewReport из комментария
       ├─► Форматирует feedback
       ├─► CoderAgent: исправляет код
       │
       ▼
┌─────────────────┐
│  Pull Request   │
│  (iteration=2)   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Review Agent    │
│  (повторно)     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Review Comment  │
│ verdict: PASS   │
│ + лейбл:approved│
└─────────────────┘
```

### Детальный поток Code Agent

```
1. CodeWorker получает Issue #42
   │
2. Создает ветку: agent/issue-42
   │
3. Проверяет существующий PR → определяет iteration
   │
4. RepoContextBuilder строит контекст:
   ├─► tree_summary (структура репозитория)
   ├─► readme (первые 50 строк README.md)
   ├─► agents_md (AGENTS.md если есть)
   ├─► build_files (pyproject.toml, requirements.txt, etc.)
   └─► tests_hint (конфигурация тестов)
   │
5. SGRCoderAgent генерирует план:
   ├─► Input: repo_context + tools + issue_body
   ├─► Output: SGRPlan (структурированный JSON)
   └─► План содержит 3-5 шагов с целями и инструментами
   │
6. CoderAgent выполняет план:
   ├─► Шаг 1: list_directory → находим src/
   ├─► Шаг 2: read_file → читаем src/main.py
   ├─► Шаг 3: update_file → обновляем src/main.py (полный файл)
   └─► ... до завершения плана
   │
7. CoderAgent генерирует CoderResult:
   ├─► success: bool
   ├─► summary: str
   └─► files_modified: list[str]
   │
8. CodeWorker коммитит и пушит изменения
   │
9. Создает/обновляет PR с IterationState в теле
```

### Детальный поток Review Agent

```
1. ReviewWorker получает PR #123
   │
2. Извлекает:
   ├─► PR diff (через GitHub API)
   ├─► CI conclusion (из env или GitHub API)
   └─► IterationState (из PR body)
   │
3. RepoContextBuilder строит контекст
   │
4. SGRReviewerAgent генерирует план ревью:
   ├─► Input: repo_context + tools + issue_body + pr_diff
   ├─► Output: SGRPlan для ревью
   └─► План содержит шаги: какие файлы проверить, что искать
   │
5. ReviewerAgent выполняет план:
   ├─► read_file (измененные файлы из diff)
   ├─► grep_search (поиск паттернов, связанного кода)
   └─► Анализирует код на:
       ├─► Качество кода
       ├─► Соответствие best practices
       ├─► Потенциальные баги
       ├─► Безопасность
       └─► Соответствие AGENTS.md правилам
   │
6. ReviewerAgent генерирует ReviewReport:
   ├─► verdict: "PASS" | "FAIL"
   ├─► summary: краткое резюме
   ├─► changes: list[RequestedChange]
   │   ├─► file: путь к файлу
   │   ├─► description: описание проблемы
   │   ├─► rationale: обоснование
   │   └─► severity: "blocker" | "major" | "minor"
   ├─► positives: список положительных моментов
   └─► risks: потенциальные риски
   │
7. ReviewWorker:
   ├─► Форматирует комментарий (человекочитаемый)
   ├─► Встраивает JSON в скрытый комментарий
   ├─► Комментирует PR
   └─► Управляет лейблами (agent:approved / agent:fix)
```

## 🔍 Observability

Система использует **Langfuse** для observability всех операций.

### Что логируется:

- **LLM вызовы** (`LLM.invoke`): все запросы и ответы с полными промптами
- **Агенты** (`CoderAgent.run`, `ReviewerAgent.run`): входные контексты и результаты
- **SGR агенты**: планы генерации
- **Tools**: все вызовы инструментов с параметрами и результатами

### Настройка Langfuse:

```bash
export LANGFUSE_SECRET_KEY="sk-..."
export LANGFUSE_PUBLIC_KEY="pk-..."
export LANGFUSE_BASE_URL="https://cloud.langfuse.com"  # опционально
```

Если ключи не заданы, Langfuse просто не инициализируется (graceful degradation).

## 🛠️ Технические детали

### Итерации и защита от циклов

Система отслеживает итерации через `IterationState`:

```python
@dataclass
class IterationState:
    issue_number: int
    iteration: int
    max_iterations: int
```

`IterationState` хранится в скрытом комментарии в теле PR:

```markdown
<!-- agent:issue=42 iter=2 max=5 -->

[Обычное описание PR]
```

Это позволяет:
- Отслеживать количество итераций
- Предотвращать бесконечные циклы
- Восстанавливать состояние при повторных запусках

### RepoContext

`RepoContext` предоставляет агентам структурированную информацию о репозитории:

```python
class RepoContext(BaseModel):
    repo_path: str
    tree_summary: str              # Структура директорий
    readme: str | None             # Первые 50 строк README.md
    agents_md: str | None          # AGENTS.md (правила репозитория)
    build_files: str | None        # Информация о build файлах
    tests_hint: str | None         # Конфигурация тестов
```

### Структурированные выходы

Все агенты возвращают структурированные данные через Pydantic модели:

- `CoderResult`: результат работы Code Agent
- `ReviewReport`: результат Review Agent
- `SGRPlan`: план от SGR агентов

Используется `openai.chat.completions.parse()` для прямого парсинга в Pydantic модели.

### Git Provider интерфейс

`GitProvider` абстрагирует работу с GitHub API:

```python
class GitProvider(ABC):
    @abstractmethod
    def get_issue(self, number: int) -> Issue: ...

    @abstractmethod
    def create_pr(self, title: str, body: str, head: str, base: str) -> PullRequest: ...

    @abstractmethod
    def get_pr_diff(self, number: int) -> str: ...

    # ... и другие методы
```

Это позволяет легко переключиться на GitHub App или другой провайдер.

## 📦 Docker образ

Multi-stage Dockerfile для оптимизации размера:

```dockerfile
FROM python:3.11.9-slim AS base
# ... поэтапная сборка
```

**Итоговый образ содержит:**
- Python 3.11.9
- Git
- Все зависимости из `pyproject.toml`
- Исходный код проекта

**Размер:** ~200-300MB (зависит от зависимостей)

## 🎯 Best Practices

### Для репозиториев, использующих агента

1. **Создайте `AGENTS.md`** с правилами:
   ```markdown
   # Agent Rules

   - Используйте type hints везде
   - Следуйте PEP 8
   - Тесты должны быть в tests/
   - Запуск тестов: `pytest tests/`
   ```

2. **README.md** должен быть кратким (первые 50 строк используются в контексте)

3. **Структура проекта** должна быть понятной (агент использует `list_directory`)

### Для GitHub Actions

1. Используйте `concurrency` группы для предотвращения конфликтов
2. Устанавливайте правильные `permissions`
3. Используйте `fetch-depth: 0` для полной истории git
4. Передавайте `CI_CONCLUSION` в Review Agent

## 🔐 Безопасность

- **Path traversal protection**: все tools проверяют пути через `os.path.commonpath`
- **Git apply validation**: патчи валидируются перед применением
- **Python syntax validation**: автоматическая проверка синтаксиса перед сохранением
- **Атомарные операции**: файлы обновляются через временные файлы

## 📝 Лицензия

[Укажите лицензию]

## 🤝 Вклад

[Инструкции по контрибуции]
