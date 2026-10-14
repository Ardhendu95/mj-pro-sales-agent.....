# mjPROConnect — interview demonstration

## Open the demonstration

First use on a new laptop: complete `OPEN-ME-FIRST.md` before starting.

Double-click `START-DEMO.cmd` in this folder. Keep its window open. Once it says to open the site, visit http://127.0.0.1:8011. The sales workspace is http://127.0.0.1:8011/admin; username `admin`, with the password chosen during private setup. Do not put that password or the Gemini key in slides, screenshots, or this guide.

If the application is already running, open the site directly. If Docker reports an error, stop setup and read the error; do not reset or remove its database. `CONFIGURE-DEMO.cmd` opens the private setup form if configuration needs attention.

## Three-minute speaking script

Use a fresh chat and fictional information. AI waiting time can extend the three-minute speaking time. Never pretend a saved screenshot is a live answer.

**0:00–0:25 — The problem**

“This demonstration helps a supplier move from an initial question to a useful sales enquiry. The visitor gets information first, and the sales team receives a reviewed callback request. It runs locally and does not make real calls or send emails.”

Point to **Ask → Understand → Connect with sales**. Open the small chat launcher.

**0:25–1:05 — A useful answer with evidence**

Type: **We supply industrial fasteners. How could mjPROConnect help us?**

“This answer comes from real Gemini using reviewed public information. I can open ‘Why this answer?’ to inspect the supporting excerpt, document title and review date. ‘Details you’ve shared’ shows information retained from the visitor, rather than asking for it again.”

Open the evidence and shared-details disclosures. Only describe details actually shown.

**1:05–1:40 — Explain the commercial offer honestly**

Type: **Compare six months with twelve months.**

“The reviewed records list ₹15,000 for six months and ₹25,000 for twelve months. Both include the same features. Tax treatment is unspecified; the assistant must not invent it.”

Type: **Are orders guaranteed?**

“The available information does not establish an order guarantee. Where evidence is insufficient, the assistant offers human follow-up.”

**1:40–2:20 — Review before saving**

Click **Talk to sales**. Use the following fictional details:

| Form field | Example |
|---|---|
| Your name | Demo Visitor |
| Company | Example Manufacturing |
| Products or services | industrial fasteners |
| Target buyers | industrial buyers |
| Email | visitor@example.invalid |
| Preferred callback time | Tomorrow, 2–4 pm |

Leave optional experience and phone blank. Click **Review request**, review the details, tick consent, and click **Save callback request**.

“A callback is saved only after consent. Repeating the same submission does not create a second handoff. The request remains in this local demonstration.”

**2:20–3:00 — Show the result for sales**

Open the sales workspace and sign in privately. Filter by **Example Manufacturing**. Expand **View questions and context**. Show products, target buyers, callback preference and the next action. Open **Read conversation**, then change the follow-up status to **In progress**.

“Sales can see what the supplier wants and what they asked. Missing form information is shown as ‘Not provided’. The original transcript and recorded consent remain available, so the team can verify the brief.”

## Architecture in plain English

The React page is the visitor's front desk. FastAPI is the coordinator: it checks requests and controls what the AI can do. PostgreSQL is the local filing cabinet for conversations, approved information, callback requests and usage records. Its pgvector extension helps retrieve information by meaning. Gemini chooses from three restricted tools and writes the answer using retrieved evidence.

The flow is: visitor message → server → approved information or structured plans → Gemini answer → server checks → answer and evidence on screen. A separate reviewed form → consent → database transaction saves the lead and callback together. An optional Gemini summary happens after saving; its failure does not erase the callback.

## Five likely interview questions

1. **Why use AI instead of a fixed FAQ?**
   Visitors can phrase questions naturally and ask follow-ups. AI retrieves information and explains it in context; plans and callback submission remain controlled by the application. This prototype does not yet prove better conversion rates than a normal FAQ.

2. **How do you reduce invented answers?**
   Retrieval excludes unapproved, confidential and archived information. Each accepted claim needs a valid source and an exact evidence quote; numeric values are checked against that quote. These checks reduce risk but do not prove that every paraphrase logically follows from its source. The visible excerpts and original transcript support human review.

3. **What happens if Google fails or its free quota runs out?**
   Temporary server errors receive at most one automatic retry per Google operation. Quota errors are not retried automatically. Attempts are recorded against the existing daily cap of 100 over a rolling 24 hours. The visitor sees retry/callback options; there is no hidden scripted answer labelled as live AI and no paid fallback. A message may use several Google operations, including search embeddings.

4. **How are information and access protected?**
   The key stays on the server. Administrator access uses a protected session cookie, and each visitor conversation requires its own token. Callback consent is recorded. Approved public documents and visitor chat messages go to Google; local storage does not mean all processing stays on the computer. Use fictional visitor details, especially with the free tier. The callback form is stored locally; contact fields are not sent to the optional conversation summarizer.

5. **What did you personally build, and what would you do next?**
   This prototype was implemented and debugged with AI coding assistance. Before the interview, identify only the decisions, code changes, testing and presentation work you personally performed. Do not claim sole authorship or experience you do not have. Be ready to explain one real request through the code. Next priorities would be a broader answer-quality evaluation, company approval of source material, and a proper deployment/security review before real customer use.

## Known limitations and honest claims

- This is a local demonstration, not a production installation, payment system or connected sales platform. No real calls, email, WhatsApp or external sales-system updates occur.
- Sources are public website information reviewed for this demo, not company-approved internal sales guidance. Prices can change. Tax treatment remains unspecified.
- Free Gemini availability and quota vary. The local model is configurable; the currently configured model must be checked in **Connection**. Do not promise latency or availability.
- Qualification uses explicit visitor wording and can miss a detail. The reviewed callback form is authoritative. Evidence validation is not a guarantee of zero hallucinations.
- The company filter searches the workspace's already loaded latest 100 conversations. It is not a search of every historical record. Knowledge refresh is manual; there is no automatic website crawler.

## Before presenting

Follow OPEN-ME-FIRST.md to set up your own laptop and index the approved public pack. Rehearse the complete flow with your own fictional information. Model access and quota must be checked on your own Google account. This package contains no previous conversations or screenshots. If Google is unavailable, explain that directly and demonstrate the local callback flow; never present a scripted response as live AI.

## Five-minute rehearsal

1. **Minute 1:** Explain the supplier's problem and the three-step journey without reading code.
2. **Minute 2:** Open an answer's evidence and explain what the checks do and do not prove.
3. **Minute 3:** Explain the two subscription options and why orders cannot be promised.
4. **Minute 4:** Show a callback brief, consent, transcript and saved status.
5. **Minute 5:** Explain one failure case, your actual contribution and the next improvement. Keep the Google key and password off-screen.
