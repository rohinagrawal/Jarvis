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

**Status:** Complete, self-check answered. Went with Gemini. `openai` + GitHub Models was tried first, then dropped after discovering GitHub Models was fully retired July 30, 2026 (see Failure Log) — real dead-end, not a hypothetical one.

- [x] Confirm your Python version works with the libraries you'll need. `pyproject.toml` originally pinned `requires-python = ">=3.14"`, which was too new for some ML-adjacent packages (chroma, sentence-transformers, etc.) — it's now `>=3.12`, and `.venv` is running 3.12.14. If you hit install failures later on a specific package, a Python-version mismatch is still the first thing to suspect.
- [x] `.env` added to `.gitignore` (it wasn't there before — worth catching before a real key goes in it). Since narrowed to `*.env` to also catch variants like `dev.env`.
- [x] **Pick your LLM provider** — went with **Google Gemini API** (`google-genai`, model `gemini-3.6-flash`). `openai` package + GitHub Models endpoint was the first attempt; removed after the 410 retirement error (Failure Log entry below) — the leftover `github()` function now lives in `Jarvis/LLM/tasks.py` as a documented dead-end (kept, so `openai` stays a dependency; deleting both is still an option).
- [x] Core dependencies added via `uv add` as needed: `google-genai`, `openai` (only used by the dead-end `github()`, see above), `python-dotenv`.
- [x] Key loaded via `.env` (named `dev.env` locally, loaded explicitly with `load_dotenv("dev.env")`), read with `os.environ["GEMINI_API_KEY"]`, never hardcoded.
- [x] Throwaway script written (`gemini()` in `Jarvis/LLM/tasks.py`) — confirmed working: ran it, got a real response back from the model.

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

**Corpus decision:** `LEARN.md`. A GraphRAG extension using college project reports (entities/relationships: project → technologies → teammates) was discussed as a possible future phase — deliberately deferred, not scoped in yet.

**Chunking strategy — fully specified, ready to implement:**
1. **Primary split**: on `##` headers (not `#` — too coarse; not `###` — too granular and inconsistent).
2. **Fallback split**: within an oversized `##` section, split by paragraph.
3. **Token limit**: caps every chunk at both levels. Anything still oversized after structural splitting (including a single paragraph that alone exceeds the limit) gets hard-cut at the token limit — no special case, same mechanism reused recursively.
4. **Overlap**: applied only at token-limit cuts, never at header boundaries — header boundaries are deliberate/semantic (the author already decided "new topic here"), so overlap there would just duplicate content with no benefit. Token-limit cuts are arbitrary (land wherever the count hits), which is exactly where context can be split mid-thought.
5. **Merge**: a small chunk merges into the earlier chunk only if (a) that earlier chunk is from the *same* `##` section, and (b) the small chunk resulted from a token-limit cut, not a header split. No same-section earlier chunk to merge with → stays standalone.
6. **Header-splits stand as-is, always** — never merged, never touched, regardless of how small they end up (e.g. a short subsection with just a couple of bullets stays its own chunk). Deliberately accepted trade-off: occasionally thin/context-poor chunks, in exchange for a single consistent rule with no cross-topic-boundary exceptions.
7. **Oversized paragraph** (rare edge case): not special-cased — falls through to rule 3 (hard-cut) and rule 4 (overlap) like any other token-limit overflow.

This is recursive/hierarchical chunking (headers → paragraphs → hard token cutoff), same concept as LangChain's `RecursiveCharacterTextSplitter`, derived independently before reading `LEARN.md` 2.1's coverage of it.

**Status:** Complete (`Jarvis/Chunking/tasks.py`, constants in `constants.py`); chunks read and reviewed; self-check answered. On `LEARN.md` it yields 69 chunks, max 325 words (heading included). Token counting is a crude word count (`count_token_approx` in `utils.py`), deliberately swappable later for a real tokenizer.

- [x] Implement the strategy above. Each chunk is a `Chunk_MD(text, section, from_token_cut)`; `section` is the real `##` heading, and that heading line is also prepended to the text of every chunk from the section (its tokens count against the limit, so the body budget is `TOKEN_LIMIT` minus the heading).
- [x] Print out a handful of actual chunks and read them. Would a chunk on its own, with no surrounding context, make sense to someone who didn't already know the document? Done — reading them showed that chunks cut from the middle of a section (e.g. the hard-cut chunk in 4.1, which starts mid-sentence) lose their topic, which led to the decision to prepend the `##` heading to every chunk.
- [x] Decide the actual token limit number empirically — started at 400/100 (51 chunks, hard-cut path never triggered on `LEARN.md`), moved to `TOKEN_LIMIT = 300`, `OVERLAP_TOKEN = 100` (hard-cut path now runs on real data: 2 token-cut chunks, in sections 4.1 and 5.3). `FLOOR_TOKEN_LIMIT = 50` is the tail-merge threshold, raised from 20 because thin chunks do not embed properly.

**Self-check:**
- Why this chunk size and overlap, specifically? "Seemed reasonable" isn't an answer that survives a follow-up question.
- What part of your corpus would this strategy handle badly (a table, a code block, a long bullet list)? If the honest answer is "nothing, my corpus is all prose," say so, but know that's a simplification you made, not a universal truth about chunking.
- If you doubled the chunk size, what would you expect to get better and what would get worse?

**My answers (own words):**
1. *Why 300 words with 100 overlap?* Trial and error. Generated 400-word chunks, read them, and found they contained multiple ideas; some also had no heading, which made the topic unclear. So I chose 300 and made the heading part of that 300. A chunk should hold one full idea; 300 words gives roughly two. It's a starting point, to be refined if needed. The 100-word overlap only applies at hard cuts, which are rare here (2 of 69 chunks), so it hasn't been tuned. *(Still to add: why 100 and not, say, 50.)*
2. *What does this strategy handle badly?* Tables and bullet lists get their structure destroyed when cut. The chunk size is a bit big and can hold two ideas, which means less accurate retrieval. `###` subheadings and line breaks get lost in hard cuts. `###` subheadings are also not chunk boundaries — a design choice (`###` is too granular and inconsistent, and would produce many tiny chunks). The cost is that a chunk can span two subtopics under one `##` heading and carries only that parent heading. Accepted for now; if retrieval shows subtopics getting mixed, the fix is to split on `###` only inside oversized `##` sections. *(Could add: header-split chunks can be very small, e.g. 21 words.)*
3. *What does doubling the chunk size change?* Better: fewer cuts, more context. Worse: uses the context window faster, lost in the middle, weaker embeddings. *(Could add: one vector averages several topics; embedding models have a maximum input length.)*

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
| 0 | Used Google Gemini API (`google-genai`) as the LLM provider | GitHub Models was the first choice (free via existing GitHub Student Pack PAT, zero extra signup), but it turned out to be fully retired (July 30, 2026) before it could be used. Gemini was the next-best option: free tier with looser quota restrictions than the other free alternatives. | Considered Groq and OpenRouter but didn't seriously evaluate either — current need (one working call, Phase 0's whole scope) was already covered by Gemini's free tier. Decision was deliberately deferred: Groq/OpenRouter stay on the table specifically for when multi-model orchestration becomes a real requirement (later phases), not decided against on technical merit now. |
| 1 | Chunking strategy: recursive/hierarchical — split on `##` headers, fall back to paragraph split within oversized sections, hard-cut at a token limit as the final fallback | `LEARN.md` has strong structural signal (real Markdown headers) to split on, so rule-based/deterministic chunking was a clear fit — an LLM-based semantic chunker would be solving a problem this corpus doesn't have (no structural signal to substitute for). Considered chunking on paragraph breaks alone first, rejected because related content under one header was getting scattered across unrelated chunks. | Considered LLM-based/semantic chunking (using an LLM or embedding similarity to find topic boundaries) — rejected as unnecessary complexity, cost, and non-determinism for a document that already has clean structural markers; noted as the right tool for corpora that lack that structure (unformatted prose, transcripts). |
| 1 | Split on `##` only; `###` subheadings are not chunk boundaries | `##` sections in `LEARN.md` are the topic-level units; `###` is too granular and inconsistent across the file (62 of them), so splitting on it would produce many tiny chunks. | Splitting on `###` too gives sharper topic boundaries, but thin, context-poor chunks. Accepted cost: a chunk can span two subtopics and carries only its `##` heading. Mitigation if retrieval shows mixed subtopics: split on `###` only inside oversized `##` sections. |
| 1 | Overlap only at token-limit cuts; merge only for token-limit-cut fragments within the same header section; header-splits never merged regardless of size | Header boundaries are deliberate semantic boundaries (the author decided "new topic here") — overlap/merge there would either duplicate content for no benefit or mix unrelated topics into one chunk. Token-limit cuts are arbitrary (land wherever the count hits) and are the only place context genuinely needs patching. | Considered merging small header-split sections into an adjacent (different-topic) section for size consistency — rejected because it violates the same-topic-per-chunk principle; accepted the trade-off of occasional thin/context-poor small chunks instead, in exchange for one consistent rule with no cross-topic exceptions. |
| 1 | Heading prepended to the text of every chunk (and also kept in `section`); heading tokens count against `TOKEN_LIMIT` | Found by printing and reading real chunks: a mid-section chunk with no heading (e.g. one starting "state object); long-term = ...") has no topic on its own, so it is hard to understand, embed or cite. `section` also gives rule 5 its same-section check. | Keeping the heading only in metadata and combining it at embedding time keeps stored text clean, but every consumer then has to remember to prepend it. Accepted cost: ~5-10 duplicated words per chunk. Known limit: `###` subheadings are not repeated, so a deep chunk carries its `##` heading but not the `###` it sits under. |
| 1 | Hard-cut tail merge: if the last window of an oversized paragraph has ≤ 50 new words (`FLOOR_TOKEN_LIMIT`), append only those new words to the previous chunk instead of making a new one | A tail made of 100 overlap words plus a handful of new ones is a near-duplicate fragment. | Accepted trade-off: a merged chunk can reach roughly `TOKEN_LIMIT + 50` (up to ~350; max seen on `LEARN.md` is 325), breaking the strict cap. Alternative was a strict cap with occasional near-duplicate fragments. |
| 1 | Hard-cut windows stop as soon as one reaches the end of the text | Looping over every start position produced a final window fully contained in the previous one. | None considered. |
| 1 | `TOKEN_LIMIT` 300 / `OVERLAP_TOKEN` 100 (from 400 / 100) | At 400 the hard-cut path never ran on `LEARN.md`; at 300 it ran once. Reading 400-word chunks showed multiple ideas per chunk and unclear topic without a heading; 300 (heading included) gives roughly two ideas per chunk. A starting point to refine once retrieval can be measured. | — |

## Failure Log

Every bug, weird behaviour, or "why is it doing that" moment goes here, with the actual root cause once you found it, not just the symptom.

| What broke | Root cause | Fix | What it taught you |
|---|---|---|---|
| GitHub Models API call returned a 410 error (`github_models_retirement_brownout`) | GitHub Models was fully retired July 30, 2026. It was recommended (by Claude, in this project's own chat) as a free option without first checking whether it was still active — the recommendation was based on stale/general knowledge, not a live check. | Kept `github()` in `Jarvis/LLM/tasks.py` as a documented dead-end (comment explains why it no longer works), switched the working path entirely to Gemini. | Don't trust an AI-suggested tool/provider/library at face value — verify it's actually still active/current before integrating, especially for anything that moves fast (free-tier APIs, SDKs, deprecating platforms). This was chosen specifically because GitHub Models seemed like the lowest-friction option (already had a GitHub PAT via Student Pack, repo already on GitHub) — the appeal of "less setup" is exactly when it's easiest to skip verifying the thing still exists. |
| Tail merge in hard-cut copied the whole last window into the previous chunk (chunk grew to 419 words, over the 300 limit) | The last window repeats the previous chunk's final `OVERLAP_TOKEN` words, and the merge appended all of them as well as the new words. | Append only `piece[OVERLAP_TOKEN:]`. | Synthetic test inputs (350–1000 words) all missed the merge case; only real data exposed it. Test boundary cases (319/320/321 words) on purpose. |

---

## Progress Checklist

- [x] Phase 0 — Setup
- [x] Phase 1 — Chunking
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
