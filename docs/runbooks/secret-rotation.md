# Secret Rotation Runbook

## When to use

Use this runbook when a tracked environment file, token, key, or credential may be compromised.

## Steps

1. Identify every provider whose credentials appear in the exposed file.
2. Rotate each credential at the provider. Record only the rotation date, not the value.
3. Revoke old sessions or keys where the provider supports revocation.
4. Remove the file from the current tree with `git rm backend/.env.production`.
5. Run `pwsh -File scripts/prepare-secret-purge.ps1` and confirm the dry-run output.
6. Install `git-filter-repo` and run `pwsh -File scripts/prepare-secret-purge.ps1 -Apply` on a dedicated local clone.
7. Verify `git ls-files backend/.env.production` returns no output.
8. Verify `gitleaks detect` returns no findings.
9. Do not force-push rewritten history until explicitly requested.
10. After approved force-push, instruct collaborators to re-clone or hard-reset their branches.

## Prohibited

- Do not paste secret values into issues, pull requests, logs, chats, or commits.
- Do not add `.env.production` to any commit.
- Do not force-push a rewritten branch without explicit approval.
