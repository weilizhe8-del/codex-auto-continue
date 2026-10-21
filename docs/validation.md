# Validation record

This record separates observed application behavior from instruction review and installer tests. It is not a reliability guarantee.

## Observed on 2026-10-21

Environment: Windows, authenticated Codex desktop app. An exact desktop build number was not captured for the original run; compatibility must not be generalized to every build or platform.

1. The skill passed the bundled skill-creator format validator.
2. A read-only `skills/list` request with refresh returned `auto-continue`, user scope, enabled.
3. A short-lived heartbeat was created with an explicit target conversation. A first single-occurrence request was rejected because it had no future run. A finite minutely rule with two counted occurrences was accepted. This is a scheduler observation, not an instruction to use unbounded retries.
4. After the interactive turn ended, an actual scheduled heartbeat arrived in that same conversation.
5. The acceptance turn read its current conversation identity and compared it with the saved target. It correctly recovered the prior user choice: continue until complete.
6. The turn paused its own test automation using the supported tool. A subsequent read confirmed `PAUSED`.

The live test performed no business task and did not exhaust quota. Private chat IDs, automation contents containing those IDs, local usernames/paths, and account details are intentionally not published. This is a maintainer-observed report, not an independently reproduced public benchmark.

## Instruction review scenarios

These cases were reviewed against the skill instructions. They are **not automated model evaluations or live end-to-end passes**.

| Scenario | Required behavior |
| --- | --- |
| Explicit enable, clear unfinished task | Bind heartbeat to this chat and objective; confirm only after tool success |
| No task or already complete | Ask for the missing objective or report completion; no new schedule |
| Same chat and same task, invoked twice | Locate by chat ID and skill marker; update, not duplicate |
| Existing different task or duplicate matches | Resolve ambiguity before mutation |
| Status request | Read only; do not activate or reset a schedule |
| Stop request | Pause only the matched schedule; do not kill unrelated processes |
| Known exhausted quota | Wait for later scheduled attempts; no substantive task execution |
| Unknown quota or multiple ambiguous buckets | Report unknown; no guessed recovery time |
| Both weekly and short windows exhausted | Use the later relevant reset, not only the five-hour reset |
| User cancels or changes to unrelated work | Pause rather than inherit a new objective |
| Input/approval needed or blocked Goal | Pause and report the required human action |
| Task passes its completion criteria | Pause its own schedule; do not archive the chat |
| Installer removed but schedule remains | Existing automation remains; user must stop it separately |

## Reproducible installer tests

Run `python -m unittest discover -s tests -v` from the repository root. Tests exercise installation/removal, explicit roots with Unicode and spaces, preservation of unrelated files, refusal to overwrite, edited or extra files, missing/corrupt/foreign receipts, traversal in receipts, missing/invalid source, rollback on a simulated write failure, and symlink refusal where the host permits symlink creation.

Local Windows result on 2026-10-21: **13 passed, 1 skipped** out of 14 tests. The skipped case required permission to create a symbolic link. Skill format validation and local Markdown link checks also passed.

GitHub Actions runs the same suite on Windows, Ubuntu and macOS. A configured workflow is not itself a passing run: inspect the Actions result for the commit you use. The tests perform no network requests or Codex model calls.

## Still unverified

- Quota-exhausted model startup followed by recovery at a natural five-hour or weekly reset.
- Whether the scheduler retains/retries failed attempts throughout such a limit window.
- Full repeated 30-minute task execution and completion under real project conditions.
- Application shutdown, sleep, restart, and catch-up behavior.
- Long-duration reliability, all account types, all desktop releases, and non-Windows app behavior.
- Native resumption of a paused/budget-limited Goal: **unsupported**, not merely untested.

## Optional acceptance procedure

With explicit user authorization, create a uniquely marked finite heartbeat in a non-sensitive chat. Save an arbitrary context fact, wait for a real scheduled turn, check that it reads the correct context and target, then have it pause itself and verify persisted state. Do not call a manually sent message a scheduler pass.

For quota testing, wait for a naturally occurring limit in an already authorized task; do not intentionally waste usage. Record app version, scheduling outcome before and after reset, target identity consistency (redacted in public), and whether task progress actually resumed. Until that evidence exists, keep quota recovery marked unverified.
