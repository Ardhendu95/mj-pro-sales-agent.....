# mjPROConnect — local Gemini sales demonstration

Start with **[OPEN-ME-FIRST.md](OPEN-ME-FIRST.md)**. First-time Windows setup is **SETUP-FIRST.cmd**; subsequent startup is **START-DEMO.cmd**. Python, Docker and your own Google key are required. This is a clean source package with no pre-existing conversations or private credentials.

The visitor asks questions, inspects supporting excerpts, compares reviewed plans and submits a callback after reviewing the form and consenting. A protected local sales workspace shows the matching brief, transcript and follow-up status.

## Show the code

| File | Responsibility |
|---|---|
| `web/demo.jsx`, `web/demo.css` | Visitor preview, chat, evidence, callback form and sales workspace |
| `app/demo.py` | HTTP interfaces, conversation access, consented handoff and administrator actions |
| `app/conversation_agent.py` | Restricted Gemini tools, evidence/numeric validation, qualification and summary |
| `app/search.py`, `app/gemini.py` | Approved retrieval, embeddings, quota tracking, timeout and retry behavior |
| `app/models.py`, `migrations/` | Database records and versioned schema |

`app/security.py` owns password checking, protected sessions and rate limiting. `app/seed.py` contains the dated public demonstration information and reviewed plan prices. `app/settings.py` reads the receiving laptop's private `.env`. `app/knowledge.py` imports documents; `app/database.py` supplies compatibility definitions used by its older retrieval helper. Runtime retrieval uses `app/search.py` and the demo models.

`web/app.js` is the prebuilt browser bundle. React's license notice is retained in the bundle. To change the interface, install Node.js and run `npm ci` then `npm run build` from this folder. No Node.js installation is needed merely to run the included bundle.

## Checks

After setup, Windows: `.venv\Scripts\python.exe -m pytest -q`. Mac/Linux: `.venv/bin/python -m pytest -q`. These are offline checks with fictional inputs and no Google requests. Their database is separate from the application database. Browser test scripts require Node.js, `npm ci`, an installed Chrome path in `CHROME_PATH`, and the isolated server `tests/serve_review.py`; they never use the receiving laptop's real Google key.

Use [DEMO-GUIDE.md](DEMO-GUIDE.md) for the interview script. Describe AI coding assistance accurately and claim only work and decisions you personally performed. There are no claims of improved sales, guaranteed orders or zero hallucinations.

Known limits: local demonstration only; manually reviewed public information; variable free Google availability; latest 100 loaded conversations in the company filter; evidence checks reduce risk but cannot establish the semantic correctness of every generated paraphrase. Contact details remain in the local callback record. Visitor chat messages and public retrieval material go to Google.

See **PACKAGE-CONTENTS.md** for the exact delivered files and SHA-256 fingerprints. Keep `.env`, newly generated records and credentials out of any later code submission.
