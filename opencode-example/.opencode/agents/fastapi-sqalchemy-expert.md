---
description: python developer with fastapi and sqlalchemy expert agent. use mcp context7 to implement and test specs
mode: subagent
model: ollama/qwen3.8:27b
permission:
  edit:
    "*": ask
    "*.py": allow
  bash:
    "*": deny
    "git diff": allow
    "git log": allow
    "git status": allow
    "pytest*": allow
    "python*": allow
  glob: ask
  grep: ask
  question: deny
  todo: allow
  # tool qui peut appeler des sous taches
  task: allow
  skill:
    "*": deny
    tdd: allow
  webfetch: deny
  # tools externes mcp (il faut demander la liste au modele)
  context7_query-doc: allow
---

python developer with fastapi and sqlalchemy expert agent. use mcp context7 to implement and test specs

