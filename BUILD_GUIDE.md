# Jarvis Build Guide

**What this is:** the working plan for building the actual project, phase by phase, with checkpoints that keep you honest about whether you actually understand what you built or just got it running.

**What this is not:** a source of finished code. Claude pairs with you on this project — explaining concepts, reviewing what you write, pushing back on your reasoning the way an interviewer would, unblocking you when you're stuck — but does not hand you working implementations. If you paste this guide's illustrative snippets straight into your codebase without understanding them, you've defeated the point of doing this project at all.

Refer back to `LEARN.md` for concepts as you go. This doc is the "what to build and in what order," not the "what the concept means" — that's LEARN.md's job.

---

## Ground rules

1. **You write the code. Claude explains, reviews, and interrogates.** If you ask for the implementation outright, expect to get redirected back to figuring it out, with hints, not a solution. This applies to *project logic* — chunking strategy, retrieval design, agent flow, etc.
2. **Exception: plain Python syntax and language mechanics get answered directly, in full.** You're new to Python specifically, not new to programming — so "how does a Python decorator work," "what's the difference between a list and a generator here," "why do I need `self`" get a straight, complete answer every time. That's not the part of this project you're supposed to be struggling to learn by discovery; the RAG/agent design decisions are.
3. **Every phase ends with a self-check you answer in your own words**, either out loud to Claude or written into the Decisions Log below, before moving to the next phase. Skipping this is how you end up with a project you can run but can't defend.
4. **If you're stuck more than ~30-45 minutes on the same bug**, ask, but say what you already tried first. "It's not working" gets you questions back, not an answer.
5. **The Decisions Log and Failure Log at the bottom aren't optional busywork** — they're the actual raw material for your interview answers. An interviewer asking "why did you chunk at that size" wants the answer that's supposed to live in that table.

---

## Project scope

**Default domain (change it if you want, but pick something and commit):** a RAG assistant over `LEARN.md` itself. This is deliberate, not lazy — you already know that content well enough to judge, by reading, whether retrieval actually got the right chunk. That feedback loop (you can tell when it's wrong) is worth more early on than a "realistic" domain you have to fact-check externally.

**Full scope, matching the "one project" already agreed on:**
- Deliberate chunking strategy (not a default library setting you didn't think about)
- Hybrid search + reranking
- A real agent loop in LangGraph (not a single fixed chain)
- 2-3 real tools
- Basic memory (short-term at minimum)
- One real guardrail (human confirmation before a side-effect action)
- A small, repeatable eval set (10-15 queries)

Each phase below builds on the last. Don't skip ahead — Phase 4's self-check assumes Phase 2 and 3 are actually done, not stubbed out.

---

## Phase 0 — Setup

**Goal:** a working environment and one successful LLM call, nothing else yet.

**Status as of 2026-09-12:** Python version fixed (see below), `.env` is gitignored, `anthropic` was added as a dependency speculatively before the provider decision below was settled — revisit whether that's still the right one once you pick a provider.

- [x] Confirm your Python version works with the libraries you'll need. `pyproject.toml` originally pinned `requires-python = ">=3.14"`, which was too new for some ML-adjacent packages (chroma, sentence-transformers, etc.) — it's now `>=3.12`, and `.venv` is running 3.12.14. If you hit install failures later on a specific package, a Python-version mismatch is still the first thing to suspect.
- [x] `.env` added to `.gitignore` (it wasn't there before — worth catching before a real key goes in it).
- [ ] **Pick your LLM provider.** Claude API is *not* free — Claude Pro (your chat subscription) doesn't include API credits, and there's no student discount for it. Since you're doing this for learning, not production, a free/no-card option is the better call. Options researched, no credit card needed for any:
  - **Google Gemini API** (via Google AI Studio) — recommended: current-gen Flash models, free, generous daily quota.
  - **Groq** — free, very fast inference, good later for the agent loop (Phase 5) where latency matters.
  - **OpenRouter** — free tier across 20+ models, capped at 50 req/day until you've spent $10 lifetime.
  - **GitHub Models** — free via your existing GitHub PAT (you have GitHub Student Pack), zero extra signup, stingier rate limits.
  - The provider genuinely doesn't matter for this phase's goal — pick one and move, don't over-deliberate it.
- [ ] Add your core dependencies via `uv add` as you need them, phase by phase, rather than dumping everything in now. You'll actually notice what each one is for that way. (Swap or remove `anthropic` depending on what you picked above.)
- [ ] Get your key into `.env` — `python-dotenv` is already a dependency, so use it, don't hardcode the key anywhere.
- [ ] Write a throwaway script that loads the key from `.env` and makes one successful call, printing the response.

**New to Python — a few things you'll hit in this phase, explained since this is language mechanics, not project logic:**
- `python-dotenv`'s `load_dotenv()` reads your `.env` file and dumps its key-value pairs into `os.environ` (Python's equivalent of `System.getenv()` in Java) — you then read the key with `os.environ["ANTHROPIC_API_KEY"]` or `os.getenv("ANTHROPIC_API_KEY")`.
- A "throwaway script" just means any `.py` file you run directly with `uv run python your_script.py` — no test framework, no `main.py` wiring needed yet.
- If a package install fails with something like `ERROR: Could not find a version that satisfies the requirement`, that's very likely the Python-version mismatch mentioned above — ask if you hit this, it's a quick diagnosis.

**Self-check before moving on:** if your key were exposed right now (committed to git, printed in a log), what would that cost you? Say the answer out loud. This isn't rhetorical — it's the instinct that should make "don't hardcode secrets" automatic rather than a rule you're following because someone told you to.

**Definition of done:** one script, one successful API call, key loaded from environment.

---

## Phase 1 — Corpus & Chunking

*(LEARN.md 2.1)*

**Goal:** a deliberately chunked version of your corpus, and enough manual inspection to trust it.

- [ ] Split `LEARN.md` (or your chosen corpus) by something structurally meaningful first — its own headers are a gift here, use them — before deciding whether you also need a token-count-based split within sections.
- [ ] Pick one chunking strategy on purpose. Not "whatever the library defaults to."
- [ ] Print out a handful of actual chunks and read them. Would a chunk on its own, with no surrounding context, make sense to someone who didn't already know the document?

**Self-check:**
- Why this chunk size and overlap, specifically? "Seemed reasonable" isn't an answer that survives a follow-up question.
- What part of your corpus would this strategy handle badly (a table, a code block, a long bullet list)? If the honest answer is "nothing, my corpus is all prose," say so, but know that's a simplification you made, not a universal truth about chunking.
- If you doubled the chunk size, what would you expect to get better and what would get worse?

**Don't yet:** touch the LLM-facing app. This phase is chunking and reading output, full stop.

---

## Phase 2 — Embeddings + Vector Store

*(LEARN.md 2.2)*

**Goal:** your chunks are embedded, stored, and searchable — and you've personally judged whether the results are actually good, not just "it returned something."

- [ ] Pick an embedding model (API-based or local).
- [ ] Pick a vector store. Chroma is the lowest-friction starting point for a first pass; move to something like Qdrant or pgvector later if you want more realism, not now.
- [ ] Embed and store the chunks from Phase 1.
- [ ] Run several test queries manually and actually read the results — don't trust a similarity score you haven't sanity-checked against your own judgment.

**Self-check:**
- Try a query that paraphrases a concept rather than using the document's exact wording. Does retrieval still find the right chunk? If not, that's the vocabulary mismatch problem from LEARN.md — you're not supposed to have solved it yet, you're supposed to have seen it happen.
- Try an exact-term query — something like "MCP" or "QLoRA." Does pure vector search reliably surface it? Note what you observe here specifically; it sets up why Phase 3 exists at all, and "I read about hybrid search" is a much weaker interview answer than "I watched vector search fail on an acronym and then fixed it."

---

## Phase 3 — Hybrid Search + Reranking

*(LEARN.md 2.2 hybrid search, 2.3 reranking)*

**Goal:** retrieval that handles both the paraphrase case and the exact-term case, plus a reranking pass that measurably improves precision.

- [ ] Add a keyword-based component (BM25 or similar) alongside vector search.
- [ ] Write your own merge/combination logic for the two result sets. Understand what you're doing here rather than calling a library function you can't explain.
- [ ] Add a reranking pass over the merged shortlist — a cross-encoder model or LLM-as-reranker, your choice, know the trade-off either way.
- [ ] Re-run the exact same test queries from Phase 2 and compare before/after reranking.

**Self-check:**
- In your own words, why can't a cross-encoder just replace vector search entirely, given it's more accurate?
- Did reranking actually change your results for the queries that were already fine in Phase 2? If nothing changed, is that because reranking isn't helping, or because your test queries weren't hard enough to show the difference? Don't let a null result go uninterrogated.

---

## Phase 4 — Basic RAG Loop

*(LEARN.md 2.5)*

**Goal:** retrieval feeding a real, citation-aware answer — and a deliberate test of what happens when the answer genuinely isn't in your corpus.

- [ ] Wire retrieval → prompt construction → LLM call → answer.
- [ ] Structure this so you can trace which retrieved chunk contributed to which part of the answer. If you can't do this, you can't debug a wrong answer later, only guess at it.
- [ ] Deliberately ask something your corpus doesn't cover. Watch what happens.

**Self-check:**
- What's your actual instruction to the model about only answering from retrieved content, and how confident are you it's being followed rather than just usually working?
- What did the out-of-corpus query actually do? If it hallucinated, that's your Phase 4 finding, not a failure — go note it in the Failure Log with what you changed in response.

---

## Phase 5 — Turn It Into an Agent (LangGraph)

*(LEARN.md 3.2, 4.1)*

**Goal:** an actual decide-act-observe loop, not a fixed pipeline with extra steps bolted on.

- [ ] Model the RAG call as one node in a LangGraph graph.
- [ ] Add at least two tools beyond retrieval — pick something that actually fits your domain rather than a token calculator you'll never use again.
- [ ] Let the agent decide whether and which tool to call. If you're hardcoding when a tool fires, you've built a chain, not an agent — go back and fix that before moving on.
- [ ] Add an explicit step/iteration limit so a bad loop can't run forever.

**Self-check:**
- Deliberately try to break it. Give it an ambiguous query, or write a vague tool description on purpose, and watch what goes wrong. What happened, and what did you change? This is genuinely your Layer 4 "why agents fail" interview answer, earned instead of memorised — write it in the Failure Log while it's fresh.

---

## Phase 6 — Memory

*(LEARN.md 4.1 memory)*

**Goal:** the agent behaves differently because it remembers something, not just because the conversation history got longer.

- [ ] Confirm short-term memory works: does the agent correctly use something said two turns ago in the same session?
- [ ] Optional stretch: persist one fact across separate runs (a file, sqlite, anything simple) — this doesn't need to be Graphiti-level, it just needs to demonstrate you understand the short-term vs. long-term distinction practically, not just as a definition.

**Self-check:**
- What's the actual mechanism carrying state between turns in your implementation? If your honest answer is "the whole message list just keeps growing," that's a real design choice with a real cost (context budget, Layer 1.3) — name that cost rather than treating it as free.

---

## Phase 7 — One Real Guardrail

*(LEARN.md 5.6)*

**Goal:** one action in your agent that requires a human to say yes before it happens.

- [ ] Pick one action with a real or simulated side effect (a stubbed "send an email," a destructive-sounding action, anything with consequence).
- [ ] Make the agent pause and require explicit confirmation before that action executes. Not a warning it prints and proceeds past — an actual stop.
- [ ] Optional: add one input guardrail (reject an obviously out-of-scope query) or output guardrail (validate output against an expected shape) as well.

**Self-check:**
- What specific failure does this guardrail prevent? Describe a concrete scenario where skipping it causes real harm, not an abstract "it's safer."

---

## Phase 8 — Eval Set

*(LEARN.md 5.2/5.3 eval discipline)*

**Goal:** a repeatable, scriptable check of whether your system still works, instead of manual spot-checking every time.

- [ ] Write 10-15 test queries with expected *behaviour*, not just expected exact text — "should retrieve the chunk about reranking," "should refuse and say it doesn't know," "should call the calculator tool."
- [ ] Run these as an actual script, not copy-paste testing in a terminal.
- [ ] Re-run this eval set after every meaningful change from here on. This is what "did I just break something" looks like without vibes.

**Definition of done:** one command that prints a pass/fail summary.

---

## Phase 9 — Polish for Interview Defensibility

**Goal:** the project is something you can walk through end to end, unscripted, under questioning.

- [ ] Fill in the Decisions Log below completely, for every real choice you made (chunk size, vector store, reranker, guardrail, memory approach) — one line each on why, not what.
- [ ] Fill in the Failure Log for everything that broke and how you found and fixed it. This is your Layer 6 material, directly.
- [ ] Do a dry run: explain the whole system out loud, start to finish, in under three minutes, with no code open. If you can't, that's not a failure, that's information about what to revisit before an actual interview.
- [ ] Replace the default `uv init` README with one that actually describes the architecture, not the boilerplate "Run: `uv run python main.py`" placeholder currently there.

---

## Decisions Log

Fill this in as you go, not retroactively at the end. One row per real decision.

| Phase | Decision | Why | Trade-off you considered and rejected |
|---|---|---|---|
| | | | |

## Failure Log

Every bug, weird behaviour, or "why is it doing that" moment goes here, with the actual root cause once you found it, not just the symptom.

| What broke | Root cause | Fix | What it taught you |
|---|---|---|---|
| GitHub Models API call returned a 410 error | GitHub Models was fully retired July 30, 2026 — the docs/tutorial I followed hadn't caught up | Removed the `github()` function, switched entirely to Gemini | ... |

---

## Progress Checklist

- [ ] Phase 0 — Setup
- [ ] Phase 1 — Chunking
- [ ] Phase 2 — Embeddings + Vector Store
- [ ] Phase 3 — Hybrid Search + Reranking
- [ ] Phase 4 — Basic RAG Loop
- [ ] Phase 5 — Agent (LangGraph)
- [ ] Phase 6 — Memory
- [ ] Phase 7 — Guardrail
- [ ] Phase 8 — Eval Set
- [ ] Phase 9 — Polish

---

## How to actually use Claude on this project

Good uses: asking why something works the way it does, asking Claude to review code you've already written and poke holes in it, asking Claude to play interviewer and push back on your explanation of a phase, getting unstuck on a specific error after you've said what you tried, sanity-checking whether a self-check answer is actually right, and — since Python itself is new to you — any plain syntax/language-mechanics question (decorators, generators, `async`/`await`, `self`, type hints, whatever). Those get answered directly and fully, no redirect.

Not good uses: asking for the *project's* implementation outright — the RAG pipeline, chunking logic, agent graph, etc. You'll get redirected back to this guide instead, on purpose — that redirect is the point of doing the project this way rather than being handed a finished repo. The redirect is specifically about project logic, not about Python as a language.
