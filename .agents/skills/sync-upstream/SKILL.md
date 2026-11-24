---
name: sync-upstream
description: Import PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor changes (commits on dev_extracted_libraries or open upstream pull requests) into this fork while preserving every intentional difference recorded in FORK.md. Use for upstream merges, cherry-picks of upstream PRs, conflict resolution, or refreshing the upstream snapshot.
---

# Import upstream into this fork

Upstream is abandoned (last push 2026-02-20), so most imports are single open upstream pull
requests, not branch merges. Never overwrite a documented difference just because an upstream change
applied cleanly.

Read these before touching the tree:

1. [`FORK.md`](../../../FORK.md): the active differences, the compatibility promise and the snapshot.
2. [`fork-differences.md`](fork-differences.md): each area mapped to its files and proof.
3. [`AGENTS.md`](../../../AGENTS.md): local checks, the test rule and who decides what ships.

The compatibility promise is permanent unless the maintainer changes it: the domain
`xiaomi_cloud_map_extractor`, the folder, `xiaomi_cloud_map_extractor.zip`, config entry keys,
entity unique ids and storage names stay exactly as they are.

## 1. Preflight

```sh
git status --short          # must be clean
git fetch upstream
git fetch origin
pre=$(git rev-parse HEAD)
git log --oneline "$pre..upstream/dev_extracted_libraries"
```

Upstream `master` is the v2 line and is never imported into `master`. Work on a branch from
`origin/master`:

```sh
git switch -c "import/upstream-pr-<number>" origin/master
```

## 2. Import

An upstream pull request: fetch it and cherry-pick with provenance.

```sh
gh pr view <number> -R PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor --json baseRefName,commits,files
git fetch upstream pull/<number>/head:upstream-pr-<number>
git cherry-pick -x <commits>
```

Check the base first: a PR against upstream `master` (v2) or `dev` has to be ported to the v3 code,
not cherry-picked. When several upstream PRs fix the same problem (the Ijai decryption PRs are the
example), pick one implementation, port the useful parts of the others, and name every source PR in
the commit message. A branch-level import of new upstream commits uses
`git merge --no-ff upstream/dev_extracted_libraries`.

## 3. Resolve conflicts by preserving the fork behaviour

1. Find the area in `FORK.md` and `fork-differences.md`.
2. Read both sides. Keep the upstream improvement and reapply the fork behaviour around it.
3. Never take one whole side with `--ours`/`--theirs` unless the other side is provably obsolete.
4. Never delete a fork test, a `FORK.md` row, an anchor or this skill to make the import pass.

## 4. Verify

Every imported fix follows the test rule in `AGENTS.md`: a test that fails without the imported
change and passes with it. Then:

```sh
ruff check .
pytest
git diff --check
```

Run the proof for every area in `fork-differences.md` the import touches, and look for renamed
domains, deleted tests, restored `automerge.yaml`/`lint_python.yml` or upstream URLs in the manifest.

## 5. Record it

In the same change: add a `CHANGELOG.md` entry crediting the upstream author and PR, update the
**Upstream snapshot** in `FORK.md` for branch imports, add a row for any new intentional difference,
and update the triage table in `ROADMAP.md`. Then follow "Who decides what ships" in `AGENTS.md`.
Never push to `upstream` and never comment on upstream issues or pull requests.
