Create a pull request for the current branch.

## Rules

**Title format:** `[ES-<number>] <type> <description>`

- `[ES-<number>]` - task number (e.g. `[ES-1]`, `[ES-42]`)
- `<type>` - what kind of change:
  - `feat` - new functionality
  - `fix` - bug fix
  - `chore` - formatting, docs, refactoring
- `<description>` - one line, concise summary of the PR scope

**Examples:**
```
[ES-1] feat deploy + .github/workflow setup k8s deploy
[ES-12] fix api-gateway corrected timeout on hello-world calls
[ES-3] chore restructured k8s to service-first layout
```

## Steps

1. Run `git log main..HEAD --oneline` and `git diff main...HEAD --stat` to understand all changes in the branch.
2. Extract the task number from the current branch name (e.g. `ES-1/deploy-k8s` → `ES-1`). If the branch name does not contain an `ES-` prefix, ask the user for the task number.
3. Push the current branch to remote (`git push -u origin HEAD`). Never switch branches — always push the branch you are on.
4. Create the PR using `gh pr create` with:
   - Title following the format above
   - Body with a concise summary of changes
   - Base branch: `main`
5. Return the PR URL.
