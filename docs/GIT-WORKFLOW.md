# Git Workflow — AgriSat Risk

Remote: `https://github.com/abdullah-dev5/agrisat-risk` (or your chosen repo name)

---

## Branch strategy

| Branch type | Naming | Example |
|-------------|--------|---------|
| Production | `main` | Always deployable/demo-ready |
| Module feature | `feat/m{N}-{short-name}` | `feat/m3-tier3-gee` |
| Infrastructure | `chore/m{N}-{short-name}` | `chore/m11-supabase-setup` |
| Bugfix | `fix/{short-description}` | `fix/rls-field-isolation` |

One module branch per push cycle. Merge to `main` via PR or direct merge after local verification.

---

## Commit message format

```
<type>(<scope>): <short summary>

<optional body — why, not what>
```

**Types:** `feat` · `fix` · `chore` · `docs` · `refactor` · `test`

**Scopes:** `backend` · `frontend` · `supabase` · `docs` · `tier3` · `ui` · etc.

**Examples:**
```
feat(backend): add GEE Sentinel-1 backscatter extraction for AOI
feat(frontend): support GeoJSON boundary upload with map preview
chore(supabase): apply RLS policies for institution isolation
docs: add MODULE-PLAN module acceptance criteria
```

---

## Push cycle (repeat per module)

```powershell
cd e:\AgriSat
git checkout main
git pull origin main

git checkout -b feat/m3-tier3-gee
# ... implement module ...
git add <relevant files>
git status
git commit -m "feat(tier3): integrate GEE Sentinel-1/2 and CHIRPS pipeline"
git push -u origin feat/m3-tier3-gee

# Merge when ready
git checkout main
git merge feat/m3-tier3-gee
git push origin main
```

---

## Initial push history (this repo)

| Commit | Contents |
|--------|----------|
| 1 | Foundation — README, gitignore, Supabase schema, module docs |
| 2 | Backend — FastAPI, tier adapters, fusion, risk engine, reports |
| 3 | Frontend — React scaffold, pages, map, charts |

Future modules follow the branch cycle above — one module per branch, one focused commit (or small logical series), merge to `main`.

---

## Disable Cursor co-author on GitHub (important)

Cursor may append this to commit messages:

```
Co-authored-by: Cursor <cursoragent@cursor.com>
```

GitHub then lists **cursoragent** as a contributor. To stop it:

### 1. Cursor IDE (primary)

1. Open **Cursor Settings** (top-right gear — not VS Code Settings)
2. Go to **Agents → Attribution**
3. Turn **OFF**:
   - **Commit Attribution**
   - **PR Attribution**
4. Restart Cursor

### 2. Cursor CLI / cloud agents (if you use them)

Edit `%USERPROFILE%\.cursor\cli-config.json` manually and set:

```json
"attribution": {
  "attributeCommitsToAgent": false,
  "attributePRsToAgent": false
}
```

Do not let the agent edit this file — it may revert. Run `cursor /update-cli-config` after IDE changes if available.

### 3. Git hook (backup for this repo)

```powershell
cd e:\AgriSat
powershell -ExecutionPolicy Bypass -File scripts\install-git-hook.ps1
```

Strips `cursoragent` lines even if Cursor still injects them.

### 4. Fix commits already pushed

Existing commits keep the co-author until history is rewritten. From repo root (PowerShell):

```powershell
git filter-branch -f --msg-filter "python -c \"import sys; sys.stdout.write(''.join(l for l in sys.stdin if 'cursoragent' not in l.lower()))\"" HEAD
git push --force origin main
```

GitHub’s contributor graph may take a few hours to refresh after force-push.

---

## Files never committed

- `.env`, `backend/.env`, `frontend/.env`
- `*-gee-key.json`, `service-account*.json`
- `node_modules/`, `backend/.venv/`, `frontend/dist/`

See root `.gitignore`.
