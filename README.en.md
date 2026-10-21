# Codex Auto Continue

[简体中文](README.md) · [Skill](skills/auto-continue/SKILL.md) · [Validation](docs/validation.md)

A personal skill for the Codex desktop app that schedules follow-ups **in the original conversation**. Enable it once for a clearly defined task; it attempts to return every 30 minutes, continues authorized unfinished work, and pauses its schedule when done, cancelled, or blocked on human input.

**Experimental v0.1.0.** A Windows desktop acceptance run verified same-chat wake-up, retained context, and self-pausing of the test schedule. Recovery across an actual exhausted usage window has **not** been verified. The skill is not a background service and cannot execute when the model cannot start.

## Install and use

Requires the Codex desktop app with native thread heartbeats and usage/Goal tools available in the chat. Installing this skill does not add those tools to the CLI or IDE. The optional file installer requires Python 3.10+ and uses only its standard library.

```sh
git clone https://github.com/weilizhe8-del/codex-auto-continue.git
cd codex-auto-continue
python scripts/manage_skill.py install
```

The destination is `$CODEX_HOME/skills/auto-continue`, or `~/.codex/skills/auto-continue` if unset. Existing directories are never overwritten. Alternatively, manually copy `skills/auto-continue` into your personal skills directory after checking for conflicts.

In the **task's own chat**, invoke:

```text
$auto-continue
$auto-continue status
$auto-continue stop
```

Enabled skills also appear in the desktop slash menu. Open a new turn or restart the app if it has not discovered the skill. Installation alone does not create a schedule; look for a successful automation card after activation.

The skill reuses a matching schedule, binds work to the original objective, and inherits the conversation's model and permissions. Keep the computer awake, the app running, and local project files available. It does not buy credits, switch accounts, bypass limits, or reactivate paused/budget-limited Goals. Closing the app, sleep, quota failures, and repeated 30-minute business-task runs still need broader end-to-end validation.

## Remove or update

Stop each active schedule from its chat or the app's Scheduled view **before** uninstalling. Removing the skill does not remove saved automations.

```sh
python scripts/manage_skill.py uninstall
# For an update:
git pull --ff-only
python scripts/manage_skill.py install
```

The installer refuses symlink/junction paths. Uninstall requires its receipt and unchanged package files; local edits and extra files cause a refusal rather than deletion. Manually copied skills must be removed manually. Use `--codex-home <directory>` for an explicit installation root.

## Tests and evidence

```sh
python -m unittest discover -s tests -v
```

Tests use temporary directories, no accounts or model calls. Installer tests and CI do **not** prove quota recovery. See the [validation matrix](docs/validation.md) for observed, reviewed, and untested behavior. Report OS/app versions and redacted errors, not credentials or private conversation logs.

Led by [weilizhe8-del](https://github.com/weilizhe8-del), developed with OpenAI Codex assistance. Independent community project, not affiliated with or endorsed by OpenAI. [MIT](LICENSE).
