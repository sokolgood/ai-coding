# ai-coding

src/
  cli.py
  settings.py

  application/
    code.py        # use-case: Issue -> PR (commit/push/create)
    review.py      # use-case: PR -> feedback (comment/labels)
    fix.py         # use-case: PR -> new commit (iterate)

  services/
    github.py      # GithubService (PyGithub/REST)
    git_ops.py     # GitService (subprocess git)
    workspace.py   # read/write/list/apply_patch
    retrieval.py   # search/choose relevant files (optional)
    ci.py          # run ruff/pytest locally (optional)
    logging.py     # logger init (optional)

    llm/
        engine.py      # LLMEngine interface + concrete impl (OpenAI/Yandex/etc)
        agents/
        coder.py     # CoderAgent (later)
        reviewer.py  # ReviewerAgent (later)
        tools/       # tools for llm

  types/
    github.py      # RepoRef, IssueRef, PRRef, CIStatus, ...
    results.py     # CodeResult, ReviewResult, FixResult, Verdict
    state.py       # IterationState, PRMarker parsing
