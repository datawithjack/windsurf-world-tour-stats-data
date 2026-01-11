# Plan: Merge Frontend and Backend into Monorepo

## Summary
Merge the separate frontend (React/Vite) and backend (FastAPI) repositories into a single monorepo while keeping deployments separate (Vercel for frontend, Oracle VM for backend).

## Benefits of This Approach
- Single git history for coordinated changes
- Easier local development (one terminal, one project)
- Potential for shared TypeScript types generated from Pydantic models
- Simpler project management

---

## Pre-Merge Cleanup

### Frontend Repo (this repo)

1. **Clean up git history** (optional)
   - Remove any large files from history if present
   - Ensure no secrets in commit history

2. **Remove unused files**
   - Check `src/hooks/` - currently empty, delete if not planned for use
   - Check `src/data/` - verify static data is still needed
   - Remove any `.env` files (should be in `.gitignore`)

3. **Update documentation**
   - Ensure `README.md` accurately reflects current state
   - Remove outdated docs if any

### Backend Repo

1. **Same cleanup steps** - review for unused files, secrets in history
2. **Ensure `.gitignore` is comprehensive** - no `__pycache__`, `.env`, `venv/`
3. **Document API endpoints** - helps frontend development

---

## Merge Strategy: Fresh Monorepo

Create a new repo and import both as subdirectories. Cleaner and simpler.

```bash
# 1. Create new repo
mkdir wwwts-app && cd wwwts-app
git init

# 2. Copy frontend (without .git)
cp -r ../frontend-repo ./frontend
rm -rf ./frontend/.git

# 3. Copy backend (without .git)
cp -r ../backend-repo ./backend
rm -rf ./backend/.git

# 4. Initial commit
git add .
git commit -m "Initial monorepo: merge frontend and backend"
```

---

## Post-Merge Structure

```
wwwts-app/
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   ├── vercel.json
│   └── ...
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── ...
├── .gitignore          # Combined gitignore
├── README.md           # Project overview
└── package.json        # Optional: root scripts
```

---

## Post-Merge Setup

### 1. Root package.json (optional convenience scripts)
```json
{
  "name": "wwwts-app",
  "scripts": {
    "dev": "concurrently \"npm run dev:frontend\" \"npm run dev:backend\"",
    "dev:frontend": "cd frontend && npm run dev",
    "dev:backend": "cd backend && uvicorn app.main:app --reload"
  }
}
```

### 2. Update Vercel Configuration
- Point Vercel to the `frontend/` subdirectory
- In Vercel dashboard: Settings → General → Root Directory → `frontend`

### 3. Update Backend Deployment
- Update any CI/CD scripts to deploy from `backend/` subdirectory
- Oracle VM deploy scripts should reference new paths

### 4. Combined .gitignore
Merge both `.gitignore` files, covering:
- Node: `node_modules/`, `dist/`, `.env`
- Python: `__pycache__/`, `venv/`, `.env`, `*.pyc`

---

## Optional Enhancements (Future)

### Shared Types Generation
Generate TypeScript types from FastAPI Pydantic models:
```bash
# In backend, generate OpenAPI schema
python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > openapi.json

# Generate TypeScript from OpenAPI
npx openapi-typescript openapi.json -o frontend/src/types/api.ts
```

This eliminates manual type synchronization between frontend `types/index.ts` and backend models.

---

## Verification

1. **Local development works**
   - `cd frontend && npm run dev` starts frontend
   - `cd backend && uvicorn app.main:app --reload` starts backend
   - Frontend can connect to local backend

2. **Deployments still work**
   - Push to main, verify Vercel builds from `frontend/`
   - Deploy backend to Oracle VM from `backend/`

3. **Git operations work**
   - Single `git status`, `git push` for whole project
   - Can make coordinated frontend+backend changes in one commit
