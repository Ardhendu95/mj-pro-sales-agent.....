# mjPROConnect — clean demonstration package

## Windows: first use

1. Extract the whole ZIP into a normal folder. Do not run files inside the ZIP.
2. Install **Python 3.12 or newer** from https://www.python.org/downloads/ (include Tcl/Tk and select “Add Python to PATH”). Install and open **Docker Desktop** from https://www.docker.com/products/docker-desktop/. Wait for its engine to run.
3. Double-click **SETUP-FIRST.cmd**. It checks prerequisites, explains its downloads, and asks you to type INSTALL. Internet is required. The pinned packages come from PyPI; the database image comes from Docker Hub.
4. In the private setup window, choose and repeat an admin password of at least 12 characters. Enter **your own Gemini API key** from https://aistudio.google.com/api-keys. For free use, verify billing is disabled on that Google project before ticking the confirmation. Save privately.
5. Double-click **START-DEMO.cmd**. Keep its window open. Visit http://127.0.0.1:8011. Open the sales workspace at http://127.0.0.1:8011/admin and sign in with username **admin** and your new password. In **Knowledge**, click **Re-index approved content once** to create this laptop's search index.

Indexing and chat make real requests to Google. Free quota and model access depend on your Google account. The default is `gemini-3.1-flash-lite`, which was used to verify this version. The local cap is 100 recorded attempts per rolling 24 hours, including embedding calls and failed attempts. This is a request cap, not a billing control. No paid fallback is configured.

## Later use

Double-click **START-DEMO.cmd** and open http://127.0.0.1:8011. Do not re-index every time. Your new laptop's chats and callbacks persist in its own Docker database. Stop the app with Ctrl+C; do not reset Docker or delete its volume if you need to retain those records.

## Mac or Linux

Install Python 3.12+ with Tk support and Docker with the Compose command. In a terminal opened in this extracted folder, run `python3 setup_local.py`, then `python3 run_local.py`. Use the same browser addresses and first-time indexing step above. The Mac/Linux launcher is included but has not been tested on a physical Mac/Linux machine. If Tk is missing, install the Tk component supplied by your Python/OS distributor first.

## What is included

Application source, database definitions/migration, the compiled React interface, original React source, dependency lists, offline tests and a demonstration guide. Node.js is **not required to run** the included interface. To edit/rebuild the React interface, install Node.js, run `npm ci`, then `npm run build`.

No API key, real admin password/hash, private `.env`, existing database, local conversations, transcripts, session tokens, screenshots, test results, assistant instructions, personal files or planning notes are included. Automated test inputs are fictional examples defined in source code; they are not exported user conversations. The preloaded knowledge pack contains public product information, not confidential company documents.

## If something fails

- **Python not found:** install Python with PATH enabled, then reopen SETUP-FIRST.cmd.
- **Docker connection error:** open Docker Desktop and wait for its engine to run. Do not use a factory reset as a first fix.
- **No useful AI evidence:** sign in and re-index approved information once. This ZIP starts with no existing search vectors.
- **Quota, key or model error:** check your Google project and the model in the private `.env`; configure another account-accessible model explicitly if needed. There is no hidden model substitution.
- **Port already in use:** close an already running copy of this demo. Do not stop an unrelated application without checking what it is.

This is a local demonstration. It does not send callbacks, emails or WhatsApp messages, take payments, or install itself on the real website. Google receives public retrieval material and visitor chat messages. Use fictional visitor information for a demonstration.
