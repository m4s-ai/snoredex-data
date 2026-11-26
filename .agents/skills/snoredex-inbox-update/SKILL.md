---
name: snoredex-inbox-update
description: Hermes only, on the Homelab - bring the photo inbox to the newest inbox code on main with update.sh, safely, and report the result to the owner. Use when the owner says "Update", "Eingang updaten", "Inbox aktualisieren" or "update.sh", or names a merged PR to roll out. Repository agents (Claude, Codex) never run this; for them AGENTS.md reserves it to the owner or Hermes.
---

<!-- doc: role=Homelab inbox update skill for Hermes; stage=task -->

# Snoredex inbox update

The photo inbox runs as a Docker container on the Homelab, built from the snoredex-data checkout
that holds `verification/photo_inbox/docker/compose.yaml`. A merge that changes inbox code reaches
the running inbox only after `update.sh` rebuilds it
([inbox README](../../../verification/photo_inbox/README.md), "Container on the Homelab"). The owner's word,
"Update" or the like, is the instruction for one update. It covers only the steps below.

**Private details.** The inbox's address and the checkout's path come from your own Homelab notes.
Never write them, or any host name, IP, `.env` value or token, into the repository, an issue, a PR
or a commit; snoredex-data is public. Your report to the owner in your private chat may name them.

## 1. Is an update needed?

```sh
curl -fsS "$INBOX/version"                       # code.commit, code.source, codeChanged
git -C "$CHECKOUT" fetch -q origin
git -C "$CHECKOUT" rev-parse origin/main
git -C "$CHECKOUT" diff --quiet "$RUNNING" origin/main -- \
  scripts verification/photo_inbox ':(glob)verification/*.py'; echo $?
```

`$RUNNING` is `code.commit` from `/version`.

- **Exit code 0:** the running image already has the newest inbox code. Tell the owner "Eingang ist
  aktuell" with the short commit and stop. A merge that changed only data needs no update; the inbox
  reads the synced catalogue by itself.
- **Exit code 1, or `code.commit` empty, or `code.source` not `image`:** an update is needed. Go on.
- **Any other exit code while `code.commit` is set:** git could not compare, for example because the
  running commit is not in the checkout. Do not update; send the owner the error.

## 2. Is now a safe moment?

A restart cuts off a running intake run. The run then stops as "Unterbrochen durch einen Neustart"
and needs another "Erneut versuchen" (A00, #654).

- Read `curl -fsS "$INBOX/jobs"`. If any job has `intake.run.status` `queued` or `running`, do not
  update. Tell the owner which job is running (first 12 characters of its id) and at which step, and
  wait for their word.
- The nightly round starts runs at 03:00 UTC. Between 02:55 and the end of that round's runs, wait.
- Posting needs no pause: the uploader keeps every send, and the inbox follows it again after a
  restart.

## 3. Update

```sh
cd "$CHECKOUT/verification/photo_inbox/docker"
sh update.sh
```

`update.sh` pulls `main` fast-forward, rebuilds the image with the commit it is built from, restarts
the containers and prints that commit in its short form.

If it fails, stop and send the owner its last lines:
- If the pull is not a fast-forward, the checkout has local changes or another branch. Never
  `reset`, `stash`, `checkout` or force anything.
- If the build fails, the old container keeps running.

Never touch `.env`, the secrets, `compose.yaml`, the data folder or the photo checkout. Never run
`docker compose down -v`, `docker system prune` or any other command that deletes images, volumes or
data.

## 4. Check

Within two minutes:
- `curl -fsS "$INBOX/version"` names in `code.commit` the full commit of
  `git -C "$CHECKOUT" rev-parse HEAD`, which `update.sh` printed in its short form.
- `code.source` is `image` and `codeChanged` is `false`. The page's foot then says `Code aktuell`.
- `tools.matches` is `true`: the image has the accepted tools (#681), and the foot says `Werkzeuge wie
  abgenommen`. When it is `false`, send the owner the lines under `tools.drift`; the inbox keeps
  running, and the owner decides.
- `docker compose ps` shows `inbox` and `sync` running.
- `curl -fsS "$INBOX/jobs"` answers, and no job newly reads "Unterbrochen durch einen Neustart".

If a check fails, send the owner what failed and the last 50 lines of
`docker compose logs --tail 50 inbox`. Do not roll back on your own; the owner decides.

## 5. Report to the owner

In German, short, in your private chat:

```text
Eingang aktualisiert: <alt, 8 Zeichen> → <neu, 8 Zeichen>, Code aktuell.
Neu im Eingang: #<PR> <Titel>, … (git log --first-parent --oneline <alt>..<neu> -- scripts verification/photo_inbox ':(glob)verification/*.py')
Laufende Übernahmen: keine unterbrochen.
```

When nothing was needed, send only "Eingang ist aktuell (<commit>), kein Update nötig." When you
waited or stopped, say why.
