# AGENTS.md

Rules for AI coding agents working in this repository. Human contributors follow them too.

The project is Trend Detective, a web app for the 2026 NASA Space Apps challenge. [docs/technical-spec.md](docs/technical-spec.md) defines what to build. This file defines how.

## 1. Before you write code

- Read the sections of the spec that cover your task. The spec is the source of truth for types, endpoints, statistics and wording.
- If the code must differ from the spec, change the spec in the same commit and say so in your report. Never let the two drift apart silently.
- Build in the stage order of spec section 12. Do not start a later stage's feature unless asked.
- Make the smallest change that completes the task. Add no speculative features, options or abstractions.
- Product decisions belong to the team. Implement what the spec says, and raise ideas as questions instead of building them.

## 2. Architecture rules that must not be broken

- All analysis lives in the tool layer: `backend/app/tools/`, `stats.py` and `verdict.py`. The adapters (`rest.py`, `chat.py`, `mcp_server.py`) translate inputs and outputs and never compute.
- Only `sources/power.py` calls NASA POWER. Everything else reads through the cache.
- `stats.py` is pure: no network, no files, no clock, no randomness.
- Each type is defined once, as a Pydantic model in `models.py` that mirrors spec section 5. REST, chat and MCP all reuse it.
- Every number a user sees comes from the analysis code. Verdict and summary sentences come from the templates in `verdict.py`. The AI and the frontend never calculate or reword a statistic.
- Tools are read-only and deterministic: the same inputs give the same output.
- Missing data is `None` in Python and `null` in JSON. The value `-999` never leaves the fetch layer, and a missing value is never replaced by zero.

## 3. Code style and readability

- Write code for the next reader. Prefer the obvious solution to the clever one.
- Use the spec's vocabulary in names: case, investigation, verdict, place, grid point. Keep the spec's field names exactly, such as `sen_slope` and `mk_p`.
- Put the unit in a name when it could be confused: `slope_per_year`, `slope_per_decade`.
- Keep functions short and single-purpose. Return early instead of nesting deeply.
- Type everything. Python functions have full type hints. TypeScript runs in strict mode with no `any`.
- Use no magic numbers. Thresholds such as 10 years, 20 years, 0.05 and 0.3 are named constants, defined once, with the spec section in a comment.
- Match the patterns already used in the file you are editing. Consistency beats personal preference.
- Formatting is the formatter's job. Do not hand-format, and do not reformat code you did not change.
- Leave no dead code, commented-out code or debug output behind.

## 4. Comments and docstrings

- Comment why, not what. Delete any comment that only restates the code.
- Give every public function in the tool layer and in `stats.py` a docstring. It states what the function returns, in which units, and how it treats missing values and short records.
- Point non-obvious rules at the spec, for example `# Spec 7, step 5: the correction applies only when r1 is positive`.
- In statistical code, use the spec's symbols (`s`, `var_s`, `r1`, `f`), so the code can be checked against the formulas line by line.
- Keep change history out of comments. "Fixed", "new" and "previously" belong in the commit message.
- A wrong comment is worse than none. Update or delete comments when the code changes.
- A `TODO` needs a concrete next step. Otherwise leave it out and mention the gap in your report.

## 5. Tests

- Every change in behaviour comes with a test. For a bug, first write a test that fails because of it.
- Never weaken, skip or delete a test to make the suite pass. If a test looks wrong, stop and explain why.
- The statistics must reproduce fixtures A and B of spec section 7 exactly, and must pass the seeded noise test.
- Tests are deterministic. Fix every random seed, and pass in "the last complete year" instead of reading today's date.
- Tests never touch the network. Use the saved POWER response in `backend/tests/fixtures/` and a fake for the Claude API.
- Test behaviour through public functions. Give each test one reason to fail and a name that states the behaviour, such as `test_december_counts_toward_following_year`.
- Cover the edge cases the spec names: a `-999` month, fewer than 10 years, a zero slope, tied values, no data over ocean, a clamped period.
- On the frontend, unit-test logic such as number formatting and the mapping between a URL and a case. Do not snapshot whole pages.
- Run the full test suite and the linters before you call a task done. Report what actually happened, including failures.

## 6. Errors and robustness

- Validate at the boundary: REST, chat and MCP inputs. Trust the types after that.
- Return the error codes and the error shape of spec section 10. Never send a stack trace or a raw exception to a client.
- Catch specific exceptions. Do not use a bare `except`, and do not swallow errors.
- Give every outbound call a timeout. Calls to NASA POWER follow the rules in spec section 6.
- A record that is too short, or a place with no data, is a normal result and not an error.

## 7. Security and privacy

- Secrets come from environment variables only. Never commit a key, log it or send it to the browser. Keep `.env` in `.gitignore` and keep `.env.example` up to date.
- Render user-supplied text, such as place labels and questions, as plain text and never as HTML.
- The app talks to NASA POWER, the Claude API, the OpenAI API (when it is configured instead of Claude) and the map tile server. Ask before adding any other outbound destination.
- There are no accounts, cookies, analytics or stored chat text. Logs hold the path, status and duration only.

## 8. Dependencies

- Prefer the standard library and the stack in spec section 11.
- Ask before adding a dependency. Say what it is for and why the existing tools do not cover it.
- Pin versions, and never edit a lock file by hand.

## 9. Git and change hygiene

- Do not commit or push unless asked. Never force-push or rewrite shared history.
- Keep commits small and focused. The message says what changed and why, in the imperative mood.
- Do not mix refactoring or reformatting into a feature or a fix. Mention unrelated problems instead of fixing them in passing.
- Never commit secrets, generated build output or local caches. The pre-warmed `backend/data/cache.sqlite` is the one data file that belongs in the repository.
- Write everything in English: code, comments, interface text and documents. The submission rules require it.

## 10. AI disclosure

The hackathon requires teams to show where AI was used.

- A commit that contains AI-written code or text carries a `Co-Authored-By` trailer naming the AI tool, so the commit metadata records it.
- Keep the "AI use" section of `README.md` current whenever AI writes code, text or data.
- An AI-generated image or video needs a visible watermark. Do not generate one unless asked.
- Never put NASA logos, flags or mission identifiers in generated content.

## 11. Stop and ask when

- The spec is silent, or contradicts itself, on something that changes behaviour.
- The change would alter the statistical method, a verdict template or a type in spec section 5.
- A test fails and the cause is not clearly in the code you just wrote.
- You need a new dependency, a new external service or a secret.
- The action is destructive or hard to undo, such as deleting files, data or the cache.

## 12. Definition of done

- The work meets the "Done when" of its stage in spec section 12.
- Tests and linters pass, and you have said which commands you ran.
- The spec and `README.md` are updated if behaviour, types, endpoints, configuration or data sources changed.
- Your report states what changed, what you verified and how, and what you did not verify.

## 13. Commands

These are set up in stage 1. Keep this table current.

| Task | Run in | Command |
| --- | --- | --- |
| Install backend dependencies | `backend/` | `uv sync` |
| Backend tests | `backend/` | `uv run pytest` |
| Backend lint | `backend/` | `uv run ruff check .` |
| Backend format | `backend/` | `uv run ruff format .` |
| Check backend formatting | `backend/` | `uv run ruff format --check .` |
| Run the backend locally | `backend/` | `uv run uvicorn app.main:app --reload` |
| Print a verdict | `backend/` | `uv run python -m app.cli air_temp 60.17,24.94 --label Helsinki` |
| Rebuild the example cache | `backend/` | `uv run python -m scripts.warm_cache` |
| Install frontend dependencies | `frontend/` | `npm ci` |
| Run the frontend locally | `frontend/` | `npm run dev` |
| Frontend lint | `frontend/` | `npm run lint` |
| Frontend format | `frontend/` | `npm run format` |
| Check frontend formatting | `frontend/` | `npm run format:check` |
| Frontend tests | `frontend/` | `npm run test` |
| Frontend build | `frontend/` | `npm run build` |
| Build the container | repository root | `docker build -t trend-detective .` |
| Run the container | repository root | `docker run --rm -p 8000:8000 --env-file .env trend-detective` |
