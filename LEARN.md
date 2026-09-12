# GenAI / Agentic AI Reference

**Built for:** Senior backend engineer (Java/Vert.x background) moving into AI-heavy interview rounds.
**How to use this:** Read a layer fully before moving to the next — each one assumes the last. Don't skip Layer 1 even if it feels basic; almost every "why does RAG fail" or "why does the agent loop forever" interview question traces back to a Layer 1 gap.

---

# LAYER 1 — FOUNDATIONS

## 1.1 Transformers & LLMs

### What it actually is
A transformer is a neural network architecture built around **self-attention** — a mechanism that lets every token in a sequence look at every other token and decide how much to "pay attention" to it when building its own representation. Before transformers (RNNs/LSTMs), models processed text sequentially, token by token, which made long-range dependencies hard to learn and training impossible to parallelize. Transformers process the whole sequence at once.

**Core pieces you must be able to explain from memory:**

- **Tokenization**: Text is broken into subword units (via BPE — Byte Pair Encoding, or similar) before anything else happens. "Unbelievable" might become `["un", "believ", "able"]`. This matters because model behavior on rare words, numbers, and non-English text is directly a function of how tokenization handles them.
- **Embeddings**: Each token is mapped to a dense vector. This vector is *learned*, not hand-designed — it captures semantic relationships (king - man + woman ≈ queen is the classic illustration).
- **Self-attention**: For each token, the model computes a Query, Key, and Value vector. The attention score between two tokens is roughly `softmax(Q·K / √d)`, and the output is a weighted sum of Value vectors. This is what lets "it" in a sentence correctly attend back to the noun it refers to, regardless of distance.
- **Multi-head attention**: Instead of one attention computation, you run several in parallel ("heads"), each potentially capturing a different kind of relationship (syntax, coreference, etc.), then concatenate and project.
- **Positional encoding**: Attention has no inherent sense of word order (it's permutation-invariant), so position information is injected separately — either fixed sinusoidal encodings (original paper) or learned/rotary embeddings (RoPE, used in most modern LLMs like LLaMA).
- **Feed-forward layers + residual connections + layer norm**: After attention, each token's representation goes through a position-wise feed-forward network, with residual ("skip") connections and normalization stabilizing training across many stacked layers.
- **Decoder-only architecture**: Almost all modern LLMs (GPT-family, LLaMA, Claude) are decoder-only — they generate text autoregressively, one token at a time, each new token conditioned on everything before it via **causal (masked) attention** — a token can't attend to future tokens.

### Why this matters for everything downstream
- **Context window** = the maximum number of tokens the self-attention mechanism can jointly consider. This is not a soft limit — it's architectural (attention computation is O(n²) in sequence length in the vanilla form, which is why long-context models needed architectural tricks — sparse attention, sliding windows, etc.).
- **Hallucination** is partly explainable here: the model is a next-token predictor trained to produce *plausible* continuations, not a database performing lookups. It has no built-in mechanism to say "I don't know" — it will produce the statistically likely next token even when that token encodes a false claim, unless specifically trained/aligned to hedge.
- **Why RAG exists at all**: the model's "knowledge" is frozen at training time and compressed lossily into weights. It can't know about anything after its cutoff, and it can't perfectly recall low-frequency facts. Retrieval gives it fresh, grounded, verifiable text at inference time instead of relying on parametric memory.

### Interview questions you should expect
- "Explain self-attention without using the words 'query, key, value' — then explain it again with them." (Tests if you understand it or memorized it.)
- "Why is attention O(n²) and what are the practical implications for long documents?"
- "What's the difference between encoder-only, decoder-only, and encoder-decoder architectures, and why did decoder-only win for chat-style LLMs?"
- "Why can't you just increase the context window infinitely?" (Compute cost, and — important — **attention dilution / 'lost in the middle'**: models attend less reliably to information in the middle of a long context even when technically within the window.)
- "What's the difference between a model's parametric knowledge and knowledge provided via context, and why does that distinction matter for hallucination?"
- "What is temperature and top-p/top-k sampling, and how do they affect hallucination vs. creativity trade-offs?"

---

## 1.2 Prompt Engineering

### What it actually is
Prompt engineering is the discipline of structuring input to reliably steer a model's output distribution toward what you want, without changing model weights. It sits between "hope the model does the right thing" and "fine-tune the model" — cheaper and faster than the latter, more reliable than the former if done properly.

**Techniques you need to know cold:**

- **Zero-shot vs few-shot prompting**: Zero-shot gives only instructions; few-shot gives 2-5 examples of input→output pairs before the real task. Few-shot reliably improves format adherence and reduces ambiguity, at the cost of context length.
- **Chain-of-Thought (CoT)**: Explicitly instructing the model to "think step by step" before answering. This measurably improves performance on multi-step reasoning tasks because it forces the model to generate intermediate tokens that condition the final answer — the model literally reasons *in* the output, since it has no other scratchpad.
- **Structured output / function calling**: Constraining output to JSON schemas or specific formats — critical for any system where the LLM's output feeds into code. Modern approach is native structured-output/tool-calling APIs rather than "please respond in JSON" prompting.
- **System prompts vs user prompts**: System prompt sets persistent behavior/persona/constraints; user prompt is the task. Interviewers care whether you understand system prompts are *not* a hard security boundary (see prompt injection below).
- **Role prompting**: "You are an expert X" — has a real, measurable effect on output style and sometimes quality, though it's weaker than people assume and shouldn't be relied on for factual accuracy.
- **Self-consistency**: Running the same CoT prompt multiple times with different sampling and taking a majority vote — improves reliability on reasoning tasks at the cost of N× inference calls.
- **ReAct pattern** (Reason + Act): interleaving reasoning traces with tool calls — this is the bridge into agentic AI (Layer 4).

### The production-grade concern: Prompt Injection
This is the #1 thing interviewers at senior level will push on. If a user's input (or retrieved document, or tool output) contains text like "ignore previous instructions and do X," and your system naively concatenates that into the prompt, the model may comply. Defenses: input sanitization, clear delimiter/structural separation between instructions and data, least-privilege tool access, output validation, and treating anything from an external source as **data, not instructions** (this is literally the boundary Claude itself operates under).

### Interview questions you should expect
- "Give an example where few-shot prompting would fail or backfire." (E.g., the examples bias the model toward a narrow pattern that doesn't generalize — "few-shot overfitting.")
- "How would you design a system prompt for a customer-support bot that must never discuss competitor pricing?" (Tests whether you know system prompts are strong-but-not-bulletproof — you'd combine this with output filtering.)
- "What's the difference between CoT prompting and a model's built-in 'reasoning' mode (like extended thinking)?" (CoT is prompt-elicited; reasoning models are trained/RL'd to generate extended internal reasoning by default, often in a separate channel.)
- "How do you defend against prompt injection when the untrusted content comes from a retrieved document, not the user directly?"
- "You have a prompt that works 95% of the time in testing but fails in production. Walk me through how you'd debug it." (Wants: check for distribution shift in real inputs, logging/tracing, eval harness, not just "tweak the wording.")

---

## 1.3 Context (Context Windows, Context Engineering, Context Rot)

### What it actually is
"Context" is everything the model sees at inference time: system prompt, conversation history, retrieved documents, tool definitions, tool outputs. **Context engineering** is the emerging term (arguably more important than prompt engineering at the system level) for deciding *what* goes into that limited window, in *what order*, and *how it's formatted*, given that the window is finite and attention quality isn't uniform across it.

**Concepts you need:**

- **Context window size** vs **effective context**: A model might support 200K tokens but perform measurably worse on information placed in the middle of a very long context than at the start or end — this is the "lost in the middle" phenomenon, and it's an active empirical finding, not just theory.
- **Context rot**: as conversations or documents grow very long, model performance on earlier established facts/instructions can degrade — because irrelevant or stale tokens dilute attention, and because long contexts increase the chance of contradictory or redundant information confusing the model.
- **Context budget management**: in real systems you constantly decide what to include: full conversation history vs. summarized history, top-k retrieved chunks vs. all of them, full tool schemas vs. only relevant ones. This is genuinely an architecture decision, not a minor detail — it's often the actual lever that fixes a "hallucinating" system, because the model was hallucinating due to being fed too much irrelevant context, not because it's inherently unreliable.
- **Context vs. fine-tuning vs. RAG** as three different ways to give a model information it needs — this is a decision tree interviewers love testing (see Layer 5.2).

### Interview questions you should expect
- "Your RAG system's context window supports 128K tokens. Should you always fill it with as many retrieved chunks as possible?" (No — recall/precision trade-off, cost, latency, and lost-in-the-middle effects; more context isn't free or strictly better.)
- "How would you manage context in a long multi-turn agent conversation that could run for hours?" (Summarization/compaction strategies, sliding windows, externalizing state rather than keeping everything in-context.)
- "What's the difference between giving the model information via RAG vs. via fine-tuning, from a context-budget perspective?"
- "Explain 'lost in the middle' and how it would change how you order retrieved documents in a prompt." (Put the most important chunks near the start or end, not buried in the middle.)

---

---

# LAYER 2 — RETRIEVAL & KNOWLEDGE REPRESENTATION

## 2.1 Chunking

### What it actually is
Before you can retrieve anything, you have to break source documents into pieces ("chunks") small enough to embed and retrieve individually, but large enough to preserve meaning. **This is the single most underrated lever in RAG quality** — bad chunking silently degrades everything downstream, and it's often the actual root cause when a RAG system "hallucinates" (it retrieved a chunk that was technically relevant but missing critical surrounding context).

**Strategies you need to know:**

- **Fixed-size chunking**: split every N tokens/characters, often with overlap (e.g., 500 tokens, 50-token overlap). Simple, fast, but blind to semantic or structural boundaries — can split a sentence or a table mid-way.
- **Recursive character/token splitting**: try to split on paragraph breaks first, then sentences, then words, only falling back to hard cuts when necessary. This is LangChain's default (`RecursiveCharacterTextSplitter`) and a reasonable baseline.
- **Semantic chunking**: use embedding similarity between adjacent sentences to decide chunk boundaries — split where meaning shifts, not at an arbitrary token count. More expensive (requires embedding calls at chunk-time) but produces more coherent chunks.
- **Document-structure-aware chunking**: respect markdown headers, HTML tags, code blocks — never split a function definition or a table row in half. Critical for technical/legal documents.
- **Sentence-window / parent-child chunking**: embed small chunks (for precise retrieval) but return a larger surrounding window (for full context) when a small chunk is matched. Decouples "what you search on" from "what you feed the model."
- **Chunk size trade-off**: smaller chunks → more precise retrieval (less irrelevant text per chunk) but risk losing context; larger chunks → more context per chunk but noisier embeddings (a chunk covering multiple topics embeds to a blurry average, hurting retrieval precision).

### Interview questions you should expect
- "Your RAG system retrieves the right document but the LLM still gives a wrong answer. Where would you look first?" (Chunking is a top-3 answer — the retrieved chunk may lack the context needed even though it's topically relevant.)
- "How would you chunk a 200-page technical manual with nested headers, tables, and code snippets?" (Structure-aware chunking, likely hierarchical — different strategy per content type.)
- "What's the trade-off between chunk overlap and index size/cost?"
- "When would semantic chunking be worth the extra embedding cost over fixed-size?"

---

## 2.2 Vector Databases

### What it actually is
A vector DB stores high-dimensional embedding vectors and supports **approximate nearest neighbor (ANN)** search — given a query vector, find the K most similar stored vectors, fast, even across millions/billions of entries where exact search would be too slow.

**Concepts you need:**

- **Embeddings**: numeric representations of text (or images) such that semantically similar content is geometrically close in vector space (cosine similarity or dot product/Euclidean distance).
- **Indexing algorithms**: exact nearest-neighbor search is O(n) per query — too slow at scale. ANN algorithms trade a small amount of accuracy for massive speed:
  - **HNSW (Hierarchical Navigable Small World)**: builds a multi-layer graph structure where search starts at a coarse top layer and descends — the dominant algorithm in most modern vector DBs (Pinecone, Weaviate, Qdrant, pgvector).
  - **IVF (Inverted File Index)**: clusters vectors, searches only the nearest clusters.
  - You don't need to implement these, but you should be able to explain *why* ANN exists and the recall/speed trade-off it represents.
- **Metadata filtering**: real systems almost always need hybrid queries — "find similar vectors AND where `date > X` AND `category = Y`." How well a vector DB supports pre-filtering vs. post-filtering matters a lot at scale.
- **Hybrid search**: combining dense vector search (semantic) with sparse keyword search (BM25/traditional) — because pure embedding search is bad at exact matches (product codes, names, acronyms) that keyword search handles trivially. Most production RAG systems in 2025-2026 use hybrid search, not pure vector search.
- **Popular options**: Pinecone/Weaviate/Qdrant/Milvus (dedicated vector DBs), pgvector (Postgres extension — relevant to you given backend experience), Elasticsearch/OpenSearch (hybrid natively).

### Interview questions you should expect
- "Why not just do exact k-NN search? What breaks at scale?" (Latency — O(n) becomes untenable at millions of vectors; ANN trades tiny recall loss for orders-of-magnitude speedup.)
- "A user searches for 'SKU-4471' and your vector search returns irrelevant semantically-similar results. Why, and how do you fix it?" (Embeddings are bad at exact/rare-token matching; answer is hybrid search with keyword/BM25 fallback.)
- "How would you add pgvector to an existing Postgres-based system vs. standing up a dedicated vector DB — what's the trade-off?" (Given your Java/Spring Boot background, this is a very likely question for you specifically — operational simplicity vs. purpose-built scale/features.)
- "What is embedding drift and why does it matter if you change your embedding model later?" (Old and new embeddings aren't comparable — you generally must re-embed your entire corpus, which is an operational cost people forget to plan for.)

---

## 2.3 Reranking

### What it actually is
Initial retrieval (vector search, hybrid search, or both) is a **coarse, fast first pass** — it has to scan potentially millions of candidates, so it uses cheap similarity math (cosine distance between pre-computed embeddings). Reranking is a **second, more expensive pass** applied only to the small shortlist that survives the first pass (typically top 20-100 candidates), using a more powerful model that scores relevance much more accurately — trading speed for precision, applied only where it's affordable because the candidate set is now small.

**Concepts you need:**

- **Bi-encoders vs. cross-encoders**: standard embedding-based retrieval uses a **bi-encoder** — the query and each document are encoded *independently* into vectors, then compared via cosine similarity. This is what makes it fast (documents are pre-embedded offline; only the query needs encoding at query time) but it's a structural limitation — the model never actually looks at the query and document *together*, so it misses interaction effects. A **cross-encoder** feeds the query and a candidate document *together* into the model in a single forward pass, letting it directly attend across both — much more accurate at judging true relevance, but far too slow to run against millions of documents, which is exactly why it's used only as a second-pass reranker over a pre-filtered shortlist.
- **Why this fixes real RAG failures**: pure vector similarity often returns results that are topically related but not actually the best answer — a reranker directly trained/scored on query-document relevance catches cases where "semantically close" and "actually relevant" diverge, which is a common, specific cause of a RAG system retrieving plausible-looking but subtly wrong chunks.
- **Common tools**: Cohere Rerank (API-based reranker), cross-encoder models from the `sentence-transformers` library, or LLM-as-reranker (prompting an LLM to score/reorder candidates directly — more flexible, more expensive, slower).
- **Where it sits in the pipeline**: query → initial retrieval (bi-encoder/hybrid, cast a wide net, top ~50-100) → rerank (cross-encoder, narrow to top ~5-10) → generation. This two-stage "retrieve then rerank" pattern is close to standard in serious production RAG systems now, not an optional extra.

### Interview questions you should expect
- "Why not just use a cross-encoder for retrieval directly, if it's more accurate than embedding similarity?" (Too slow/expensive to run against every document in the corpus for every query — cross-encoders require a joint forward pass per query-document pair, which doesn't scale to millions of candidates; that's exactly why the two-stage retrieve-then-rerank pattern exists.)
- "Your RAG system retrieves topically relevant but not-quite-right chunks. Would you fix this with a bigger top-K or with reranking?" (Reranking — bigger top-K just gives the generation model more noisy chunks to sift through (and risks lost-in-the-middle); reranking improves precision of *which* chunks are actually presented, which is the more targeted fix.)
- "Walk me through the two-stage retrieval architecture and why each stage exists." (Bi-encoder for fast, cheap, broad recall over the whole corpus; cross-encoder reranker for precise, expensive, narrow reordering of the shortlist — recall-then-precision, matching cheap/broad and expensive/narrow to what each stage can afford.)

---

## 2.4 Graph Databases (Neo4j)

### What it actually is
A graph DB stores data as **nodes** (entities) and **edges** (relationships), and is optimized for traversing relationships — "find all people who worked with X who also worked at company Y" is a natural, fast graph query but an expensive multi-join in a relational DB.

**Concepts you need:**

- **Property graph model**: nodes and edges both can have properties (key-value pairs) and labels/types. Neo4j is the dominant property-graph DB.
- **Cypher**: Neo4j's query language, pattern-matching based — e.g. `MATCH (a:Person)-[:WORKS_AT]->(c:Company) WHERE c.name = 'Acme' RETURN a`. You should be able to read/write basic Cypher.
- **Why graphs beat relational for certain problems**: multi-hop relationship queries ("friends of friends of friends") degrade badly in SQL (each hop = another join) but stay roughly constant-time in a graph DB because traversal follows pointers, not index lookups.
- **Where graph DBs fit in the GenAI stack**: knowledge graphs constructed from documents (entities + relationships extracted via LLM) enable **multi-hop reasoning** that vector search alone cannot do — vector search finds *semantically similar* chunks, but can't answer "how is A connected to B through C" unless that exact relationship happened to be embedded together in one chunk.

### Interview questions you should expect
- "When would you reach for a graph DB instead of a vector DB for a RAG use case?" (When the query pattern is relational/multi-hop — "who influenced whom," org hierarchies, supply chains — not just "find similar text.")
- "How do you build a knowledge graph from unstructured documents?" (LLM-based entity/relationship extraction, then dedup/entity resolution, then load into the graph — and you should flag that entity resolution is the hard, error-prone part.)
- "Write a Cypher query to find all documents connected to a given entity within 2 hops." (Be ready to sketch this even roughly.)
- "What are the operational costs of maintaining a knowledge graph that a vector index doesn't have?" (Schema/ontology design, entity resolution drift, graph maintenance as data changes — much higher engineering overhead than a vector index.)

---

## 2.5 RAG (Retrieval-Augmented Generation)

### What it actually is
The baseline pattern: given a user query, retrieve relevant chunks from an external knowledge store (usually vector DB), inject them into the prompt as context, and have the LLM generate an answer grounded in that retrieved text instead of relying purely on parametric memory.

**The pipeline, and where it breaks (know every stage):**

1. **Ingestion**: document → chunking → embedding → store in vector DB (+ metadata).
2. **Retrieval**: query → embed query → ANN search → top-K chunks. *Failure mode: query and document phrasing mismatch — a user's casual question may embed far from a formally-written document chunk that actually answers it (this is called the "vocabulary mismatch" problem).*
3. **Augmentation**: inject retrieved chunks into the prompt, usually with instructions to answer only from provided context. *Failure mode: context window overflow, lost-in-the-middle, or including irrelevant top-K results that confuse the model.*
4. **Generation**: LLM produces the answer. *Failure mode: model ignores retrieved context and answers from parametric memory anyway (especially if retrieved context is weak/contradictory), or "hallucinates" a synthesis that sounds grounded but isn't.*

**Evaluation dimensions** (this is what separates people who've built RAG from people who've read about it):
- **Retrieval metrics**: precision@K, recall@K, MRR (Mean Reciprocal Rank) — is the right chunk even being retrieved?
- **Generation metrics**: faithfulness/groundedness (does the answer actually follow from retrieved context, checkable via NLI-style entailment or LLM-as-judge), answer relevance, context precision/recall. Frameworks: RAGAS is the standard tool people cite here.

### GraphRAG
Standard RAG retrieves isolated chunks — it's weak at questions requiring you to connect information across multiple documents ("what's the relationship between these two entities that are each mentioned in different documents, never together"). **GraphRAG** builds a knowledge graph from the corpus (entities + relationships, often LLM-extracted), then retrieval traverses graph relationships in addition to/instead of pure vector similarity. Microsoft's GraphRAG paper/implementation is the reference most interviewers mean when they say the term — it also does hierarchical community detection/summarization over the graph so you can answer both specific and broad "summarize the whole corpus" style questions that pure chunk-retrieval RAG is bad at.

### Interview questions you should expect
- "Walk me through a RAG pipeline end to end and name a failure mode at every stage." (This is close to the single most common GenAI system design question — be fluent in the four-stage breakdown above.)
- "How do you evaluate whether your RAG system is actually good, beyond 'it looks right when I test it manually'?" (RAGAS-style metrics, retrieval vs generation metrics separately, held-out eval sets, LLM-as-judge with caveats about judge bias.)
- "When would GraphRAG outperform standard RAG, and what does it cost you to get there?" (Multi-hop/relational questions and whole-corpus summarization; cost is graph construction complexity, entity resolution, and higher indexing compute.)
- "Your RAG system retrieves 5 chunks but the answer needs information split across 3 different documents that were never retrieved together. What's wrong and how do you fix it?" (Chunking/embedding granularity, possibly needs GraphRAG or better query decomposition — a strong answer touches multiple layers, not just one fix.)

---

## 2.6 KAG (Knowledge-Augmented Generation)

### What it actually is
KAG is a step beyond GraphRAG: instead of a loosely-structured knowledge graph used mainly for retrieval, KAG integrates a more formal **knowledge representation** (often ontology-backed, with explicit logical/symbolic structure) with the LLM's generation, aiming for higher precision on professional/expert domains (legal, medical, finance) where GraphRAG's LLM-extracted, somewhat noisy graphs aren't reliable enough. KAG (as formalized by Ant Group's open-source framework) explicitly separates *logical reasoning* (symbolic, rule-based, precise) from *language generation* (the LLM), using the knowledge graph to constrain and verify what the LLM is allowed to assert, rather than just feed it retrieved text and hope.

**Key distinction from GraphRAG**: GraphRAG's graph is mostly a better *retrieval index*. KAG's knowledge structure is meant to be closer to a *reasoning substrate* — supporting logical inference, consistency checking, and constrained generation, not just "here's related context, go generate."

### Interview questions you should expect
- "What's the difference between GraphRAG and KAG?" (Retrieval enhancement vs. reasoning/precision enhancement with formal knowledge structure — be honest that this is a newer, less standardized area, so expect some interviewers to use the terms loosely.)
- "Why would a legal or medical application need KAG-style rigor instead of standard RAG?" (Precision/liability requirements — a hallucinated legal citation or drug interaction is unacceptable in a way a wrong restaurant recommendation isn't; formal knowledge constraints reduce that risk.)
- "What's the engineering cost of KAG vs RAG?" (Building/maintaining an ontology, formal knowledge structure, and reasoning layer is significantly more effort than a vector index — only justified when precision requirements demand it.)

---

## 2.7 RAPTOR

### What it actually is
RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) addresses a specific weakness of flat chunk-retrieval RAG: it's bad at questions requiring **high-level synthesis across an entire document** ("summarize the main themes of this book") because no single chunk contains that answer. RAPTOR builds a **tree**: leaf nodes are the original chunks; each level up is an LLM-generated summary/cluster of the nodes below it, recursively, up to a root summary of the whole document. At query time, retrieval can pull from *any level* of the tree — fine-grained chunks for specific factual questions, higher-level summary nodes for broad thematic questions — in the same retrieval pass.

### Interview questions you should expect
- "How would you handle a RAG system that needs to answer both 'what's the exact refund policy clause' and 'summarize this contract's overall risk profile' equally well?" (This is essentially describing RAPTOR's motivating use case — hierarchical retrieval solving both specific and broad queries.)
- "What's the trade-off of building a RAPTOR-style tree vs. flat chunking?" (Indexing cost — LLM calls to generate summaries at every tree level — vs. much better performance on synthesis/summarization queries.)

---

## 2.8 Agentic RAG (bridge to Layer 4)
Standard RAG is a fixed pipeline: always retrieve once, always generate once. **Agentic RAG** gives the model agency over the retrieval process itself — it can decide *whether* to retrieve at all, issue *multiple* retrieval calls with reformulated queries, retrieve from *different sources* based on query type, critique its own retrieved context and re-retrieve if insufficient, or decompose a complex question into sub-questions each requiring separate retrieval. This is covered in depth in Layer 4 once agentic concepts (tool use, planning loops) are established — flagged here because it's the natural endpoint of the RAG discussion.

---

# LAYER 3 — ORCHESTRATION FRAMEWORKS

**A note before this section**: These are Python-first frameworks, and you're coming from a Java/Vert.x background. Interviewers will more often probe whether you understand the *concepts* these frameworks implement (state management, chains of calls, tool routing) than whether you have LangChain's exact API memorized — but you should know the vocabulary and be able to sketch basic code, because "have you actually used this" is a very likely direct question.

## 3.1 LangChain

### What it actually is
LangChain is an abstraction library for building LLM applications — it provides standardized interfaces over LLM providers, prompt templates, output parsers, retrievers, and **chains** (sequences of calls: prompt → LLM → parse output → next step). Think of it as plumbing/glue code that's been standardized so you're not hand-rolling API calls and string formatting for every LLM app.

**Core concepts:**
- **Chains**: composable sequences of operations, e.g. `prompt | llm | output_parser` (LangChain Expression Language / LCEL uses the pipe operator to compose these declaratively).
- **Retrievers**: standardized interface wrapping vector DBs so chains can call `.retrieve(query)` regardless of underlying DB.
- **Document loaders & text splitters**: ingestion-side tooling (connects to the chunking discussion above).
- **Memory**: mechanisms for persisting conversation state across turns (though in modern LangChain this is increasingly handled via LangGraph's state rather than legacy memory classes).
- **Output parsers**: force LLM text output into structured types (Pydantic models, JSON, etc.).

**Known criticism you should be aware of** (senior interviewers sometimes probe this): LangChain has a reputation for heavy abstraction that can obscure what's actually happening in the underlying API calls, making debugging harder — some teams deliberately avoid it in production and call LLM APIs more directly, especially for simple use cases. Being aware of this trade-off (abstraction/speed of development vs. transparency/debuggability) shows maturity, not just tool familiarity.

### Interview questions you should expect
- "What problem does LangChain actually solve that you couldn't do by calling the OpenAI/Anthropic SDK directly?" (Standardization across providers, composability, ecosystem of integrations — but push back if asked "is it always the right choice" — for simple single-call use cases it can be overkill.)
- "What's LCEL and why did LangChain move toward it?" (Declarative composition, streaming/batching/async support built-in, more predictable than the older imperative chain classes.)
- "What are the downsides of building on a heavy abstraction framework like LangChain in production?" (Debugging opacity, version churn/breaking changes historically, potential performance overhead, vendor lock-in to their abstractions.)

## 3.2 LangGraph

### What it actually is
LangGraph is where "agentic" really lives. It models an application as a **graph of nodes and edges** where nodes are functions (often LLM calls or tool calls) and edges define control flow — critically, **edges can be conditional and the graph can cycle**, unlike LangChain's mostly-linear chains. This is what lets you build actual agent loops: "call the LLM → decide if a tool is needed → call the tool → feed result back to the LLM → repeat until done."

**Core concepts:**
- **State**: a shared, typed object that flows through the graph and gets updated by each node — this is how agents maintain context/memory across steps in a principled way (rather than just growing a message list unboundedly).
- **Nodes and edges**: nodes do work; edges (including conditional edges) decide what happens next based on current state.
- **Cycles**: the key differentiator from LangChain — a LangGraph graph can loop back on itself, which is required for iterative agent behavior (retry, reflect, re-plan).
- **Persistence/checkpointing**: LangGraph supports saving state at each step, enabling pause/resume, human-in-the-loop interruption, and time-travel debugging (rewind to an earlier state) — genuinely important for production agent reliability.
- **Multi-agent patterns**: supervisor/sub-agent architectures, where one graph routes to different specialized sub-graphs/agents based on task type.

### Interview questions you should expect
- "Why would you use LangGraph instead of just a LangChain chain for an agent?" (Chains are DAGs — no cycles; agents fundamentally need loops — decide, act, observe, repeat — so you need a graph model that supports cycles and conditional routing.)
- "How do you prevent an agent loop in LangGraph from running forever?" (Explicit max-iteration limits, state-based termination conditions, timeout/budget tracking — this is a real production concern, not a hypothetical.)
- "How would you implement human-in-the-loop approval before an agent takes a risky action (e.g., sending an email)?" (LangGraph's interrupt/checkpoint mechanism — pause graph execution, surface to a human, resume with their input.)
- "Design a multi-agent system where a supervisor routes tasks to specialized sub-agents." (Be ready to sketch this at a whiteboard level — supervisor node with conditional routing based on classifying the incoming task.)

## 3.3 LangFlow

### What it actually is
LangFlow is a **visual, low-code UI** built on top of LangChain (and increasingly LangGraph concepts) — drag-and-drop nodes representing chains/agents/tools, wired together visually instead of in code, which then exports to runnable Python/API endpoints. It's aimed at rapid prototyping and at making LLM pipeline construction accessible to people who aren't writing the underlying code by hand (or for engineers who want to prototype fast before hand-coding the final version).

### Interview questions you should expect
- "When would you use LangFlow instead of hand-writing LangChain/LangGraph code?" (Rapid prototyping, demoing to non-technical stakeholders, quickly iterating on pipeline structure — not typically for final production systems needing fine control, testing, and version control discipline.)
- "What are the limits of a visual/low-code approach for production GenAI systems?" (Harder to code-review, version control, unit test, and integrate into CI/CD compared to code-first approaches — good for exploration, risky as the sole source of truth for production logic.)

---

## 3.4 MCP (Model Context Protocol) and A2A (Agent-to-Agent Protocol)

### Why this matters right now
This is a genuine, current gap if you haven't studied it — MCP in particular comes up constantly in 2026 interviews because it's rapidly becoming the standard, and it's directly relevant to you: the tool-calling pattern you're reading about right now (Claude connecting to Google Drive, Gmail, Calendar, etc. through standardized tool definitions) is MCP in production.

### What MCP actually is
Before MCP, every LLM application that wanted to connect to external tools/data (a database, a file system, a SaaS API) had to write custom, one-off integration code for each tool, for each framework. **MCP (Model Context Protocol)**, introduced by Anthropic as an open standard, defines a common protocol for how an LLM application (the "client/host") discovers and calls external capabilities exposed by an **MCP server**. An MCP server exposes:
- **Tools**: functions the model can call (with structured input/output schemas), analogous to function calling but standardized across any MCP-compatible client.
- **Resources**: data the application can read (files, database records, API responses) without necessarily invoking a tool call.
- **Prompts**: reusable prompt templates a server can expose to clients.

**Why it matters architecturally**: it decouples tool *implementation* from the specific LLM application using it. You build one MCP server for, say, your internal ticketing system, and any MCP-compatible client (Claude, another agent framework) can use it without custom integration code — the same value proposition as a standardized API vs. bespoke point-to-point integrations, applied specifically to LLM-tool connectivity. This is also why "have you used MCP" is a very reasonable direct interview question now — it's not a niche framework detail, it's becoming default infrastructure.

### What A2A actually is
**A2A (Agent-to-Agent protocol)**, an open protocol originally introduced by Google, addresses a different connection point: not agent-to-tool (MCP's domain), but **agent-to-agent** — how one autonomous agent discovers, communicates with, and delegates tasks to a *different* agent, potentially built by a different team or vendor, without needing to know its internal implementation. Where MCP standardizes "how does an agent use a tool," A2A standardizes "how does an agent talk to another agent as a peer" — relevant specifically for multi-agent and cross-organization agent systems, where agents need to negotiate tasks and exchange results without shared code.

### Interview questions you should expect
- "What problem does MCP solve that plain function calling doesn't?" (Standardization — without MCP, tool integration code is bespoke per app/framework; MCP makes tool servers reusable across any compatible client, the same way a REST API is reusable across any HTTP client, rather than hand-wiring a custom integration for every pairing of app and tool.)
- "Explain the difference between MCP and A2A." (MCP = agent-to-tool/data connectivity; A2A = agent-to-agent communication and task delegation between independent agents — different layers of the same broader interoperability problem.)
- "If you were exposing your company's internal APIs to an LLM agent, would you write custom tool-calling code or build an MCP server? Why?" (MCP server, if you expect more than one consuming application/agent over time — the standardization pays for itself once you're not maintaining N bespoke integrations; for a single, one-off internal use case the trade-off is closer, and custom code might be faster to ship initially.)
- "What security considerations come with exposing an MCP server?" (An MCP server is effectively a new trust boundary — it can expose powerful tools/data to any client that connects, so authentication, scoping tool permissions to the minimum needed, and treating tool outputs as untrusted input on the way back are all real concerns, not hypothetical ones.)

## 3.5 Other Multi-Agent Frameworks (CrewAI, AutoGen)

### What you need to know
LangGraph isn't the only agent orchestration framework, and interviewers who work across the ecosystem will expect you to at least know the landscape, even if LangGraph is your primary depth.

- **CrewAI**: organizes agents around a **role-based "crew" abstraction** — you define agents with specific roles/goals/backstories (e.g., "researcher," "writer," "editor"), assign them tasks, and CrewAI handles the coordination/hand-offs between them. Philosophy: higher-level, more opinionated structure, faster to stand up a working multi-agent system with less low-level control than LangGraph gives you.
- **AutoGen** (Microsoft): built around **conversational multi-agent interaction** — agents are modeled as participants in a structured conversation, passing messages to each other, including patterns where agents critique or refine each other's outputs before finalizing. Strong for research/experimentation-style multi-agent setups and complex negotiation/critique patterns between agents.
- **LangGraph**, by contrast, gives you **explicit graph/state control** — you define the exact nodes, edges, and state transitions yourself, more implementation effort but far more precise control over execution flow, error handling, and state — which is generally why it's favored for production systems needing tight reliability guarantees, versus CrewAI/AutoGen's faster-to-prototype, less granular control.

### Interview questions you should expect
- "When would you reach for CrewAI or AutoGen instead of LangGraph?" (Faster prototyping of a role-based or conversational multi-agent pattern where you don't need fine-grained control over every state transition; LangGraph when you need precise, production-grade control over execution flow, error handling, and state — the trade-off is development speed vs. control.)
- "What's the core philosophical difference between CrewAI's role-based approach and LangGraph's graph-based approach?" (CrewAI abstracts coordination away from you via roles/tasks; LangGraph makes you explicitly define the control flow — higher-level convenience vs. lower-level precision.)

---

# LAYER 4 — AGENTIC AI

## 4.1 Agentic AI (core concepts)

### What it actually is
"Agentic AI" describes systems where an LLM doesn't just produce one output for one input, but operates in a **loop**: it perceives (context/tool results), reasons about what to do next, takes an action (usually a tool call), observes the result, and repeats — pursuing a goal across multiple steps with some autonomy over the path taken, rather than following a fixed pipeline a human pre-scripted.

**Core concepts you need:**

- **Tool use / function calling**: the model is given a set of tool definitions (name, description, parameter schema) and can choose to emit a structured call to one instead of a plain text answer. The *system* (not the model) actually executes the tool and feeds the result back in. Tool descriptions matter enormously — vague descriptions cause the model to pick the wrong tool or misuse parameters, a very real production failure mode.
- **The ReAct pattern** (Reason + Act): the model explicitly interleaves reasoning ("I need to check the user's order status") with actions (tool calls) and observations (tool results), in a visible loop — this was one of the foundational papers that made modern agents work reliably instead of just guessing at multi-step tasks blindly.
- **Planning**: for complex tasks, agents often first decompose the goal into sub-tasks (explicitly, via a planning step) before executing — versus purely reactive step-by-step agents that decide the next action with no upfront plan. Planning-first agents are more predictable but less adaptive to surprises; reactive agents adapt better but can wander.
- **Memory (short-term vs long-term)**: short-term = the current conversation/task state (often just the growing message history or a LangGraph-style state object); long-term = information persisted *across* sessions (user preferences, facts learned before) — usually implemented via a separate retrieval store, not just prompt history.
- **Multi-agent systems**: instead of one agent doing everything, specialized agents handle sub-domains (a "researcher" agent, a "coder" agent, a "reviewer" agent) coordinated by a supervisor/orchestrator. Trade-off: better separation of concerns and specialization vs. coordination overhead, latency (multiple LLM round-trips), and harder debugging (which agent caused the failure?).
- **Autonomy levels**: agents exist on a spectrum from "always ask permission before any action" to "fully autonomous, no human checkpoint" — production systems almost always pick a point on this spectrum deliberately based on the cost of a wrong action (see harness engineering, Layer 6).

### Why agents fail in practice (this is what gets tested)
- **Infinite/looping behavior**: an agent gets stuck retrying a failing action, or oscillates between two states, with no termination condition.
- **Tool misuse**: calling the right tool with wrong parameters, or the wrong tool entirely, especially when tool descriptions overlap in ambiguous ways.
- **Compounding errors**: in a multi-step agent, an early wrong observation or hallucinated intermediate fact propagates and corrupts every subsequent step — errors compound multiplicatively across a chain of LLM calls, unlike a single-shot query where there's only one chance to be wrong.
- **Context bloat**: every tool call and result gets appended to the running context, and long agent sessions can blow through context budgets or suffer context-rot (Layer 1.3) well before the task is done.
- **Lack of grounding/verification**: an agent claiming "I've completed the task" without the system actually verifying the claimed action happened.

### Interview questions you should expect
- "What's the difference between a chatbot with function calling and a true agent?" (A single tool call in response to one prompt is function calling; an *agent* is the looped, multi-step, goal-pursuing behavior — the distinction is the loop and autonomy over the path, not just the presence of tools.)
- "Design an agent that books a flight, given access to a search tool and a booking tool. What could go wrong, and how do you guard against it?" (Strong answer covers: confirmation before the irreversible booking action, validation that search results actually match user intent, handling ambiguous/multiple matches, timeout/budget limits, and what happens if the booking tool call fails mid-way.)
- "How do you prevent compounding hallucination in a 10-step agent chain?" (Verification/grounding at each step where feasible, keeping steps as atomic and checkable as possible, structured intermediate outputs that can be validated programmatically rather than trusting free text, and human checkpoints before high-stakes steps.)
- "When would you use a multi-agent architecture over a single agent with many tools?" (Genuine separation of concerns/specialization, parallelizable independent sub-tasks, or when a single agent's context/tool list would become unmanageably large — but flag the latency and coordination-overhead cost.)
- "How do you evaluate an agent, as opposed to evaluating a single LLM response?" (Task success rate over many runs, step-level trajectory analysis — not just final-output correctness — because two agents can get the same right answer via very different, differently-reliable paths.)

## 4.2 Speculative Decoding

### What it actually is
This is an **inference-speed optimization**, somewhat orthogonal to the agentic/RAG concepts around it, but it shows up in "how do you make LLM apps fast/cheap in production" questions. Autoregressive generation is inherently sequential — one token at a time, each depending on the last — which is slow. Speculative decoding uses a small, fast "draft" model to generate several candidate tokens ahead speculatively, then the large target model verifies all of them **in a single parallel forward pass** (verification is cheaper than generation because it can be batched/parallelized in ways sequential generation cannot). Accepted tokens are kept; the first rejected token and everything after is discarded and regenerated. Net effect: same output distribution as the large model alone, but faster wall-clock generation because you're doing fewer expensive sequential forward passes through the big model.

### Interview questions you should expect
- "How does speculative decoding preserve the exact same output distribution as the base model, if a smaller model is doing some of the generation?" (The draft tokens are *proposed*, not accepted blindly — the target model verifies each one and only accepts tokens it would have generated itself with matching probability; rejection triggers correction, so the final output distribution is mathematically identical to sampling from the target model alone.)
- "What determines the speedup you get from speculative decoding?" (How well the draft model's outputs align with the target model's — high acceptance rate = bigger speedup; a poorly matched draft model gives little to no benefit.)
- "Where does speculative decoding fit in a cost/latency optimization strategy, versus something like caching or batching?" (It's specifically a *generation latency* fix; distinct from prompt caching (reduces repeated-context cost) and request batching (throughput under load) — a full production optimization strategy usually layers several of these together.)

---

# LAYER 5 — PRODUCTION CONCERNS

## 5.1 Hallucination — Problems and Mitigations

### Why it happens (tie back to Layer 1)
An LLM is a next-token probability model, not a fact database with a "verify" step. It generates the most statistically plausible continuation given its training and context — when it lacks grounding, it will still generate something fluent and confident-sounding, because fluency and confidence are what its training rewarded, not epistemic honesty. This is *not* a bug that gets fully "fixed" — it's a structural property of how these models work, and every mitigation below is a way of constraining or checking outputs, not eliminating the underlying tendency.

**Categories of hallucination** (interviewers like this distinction — it shows you're not treating it as one monolithic problem):
- **Factual hallucination**: stating something false as true (wrong date, wrong statistic, invented citation).
- **Faithfulness hallucination** (RAG-specific): the answer doesn't actually follow from the retrieved/provided context, even if it happens to be true — the model ignored or misused its grounding.
- **Reasoning hallucination**: a chain-of-thought that looks logical step-by-step but reaches an unsupported conclusion, or invents an intermediate "fact" mid-reasoning to make the chain work.

**Mitigation techniques (know several, not just one):**
- **RAG/grounding**: give the model real, current, verifiable source material rather than relying on parametric memory — reduces but does not eliminate hallucination, since the model can still ignore or misread retrieved context.
- **Prompting for citation/attribution**: instruct the model to cite which retrieved chunk supports each claim — makes hallucination *detectable* (a claim with no valid citation is suspect) even when not fully prevented.
- **Self-consistency / multiple sampling**: generate several answers and check agreement — disagreement flags likely unreliable/hallucinated content on that specific query.
- **LLM-as-judge / verification pass**: a second LLM call specifically checks whether the first response's claims are supported by the provided context (essentially an automated faithfulness check) — useful but introduces its own cost and its own (smaller, correlated) error rate.
- **Structured output + programmatic validation**: where possible, constrain outputs to a schema/format that can be validated with actual code (does this ID exist in the database? is this date real?) rather than trusting free text.
- **Confidence/uncertainty signaling**: training or prompting the model to express calibrated uncertainty ("I'm not certain, but...") rather than uniform confidence — genuinely hard to get reliable, but increasingly a focus area.
- **Fine-tuning / RLHF for honesty**: training the model to prefer "I don't know" over confident fabrication on out-of-distribution queries — an alignment-level intervention, not something you do per-application.
- **Human-in-the-loop for high-stakes outputs**: the most reliable mitigation for anything where a wrong answer is costly — don't fully automate the decision.

### Interview questions you should expect
- "Your RAG chatbot occasionally states facts not present in any retrieved document. How do you debug and reduce this?" (Distinguish faithfulness hallucination specifically — check if it's a prompting issue (not instructed strongly enough to only use provided context), a retrieval issue (right info wasn't retrieved so the model filled the gap from parametric memory), or genuinely the model ignoring good context — each has a different fix.)
- "How would you build an automated hallucination-detection system for a production RAG pipeline?" (LLM-as-judge faithfulness scoring against retrieved context, ideally validated against a human-labeled eval set so you trust the judge's calibration, plus tracking hallucination rate as a monitored production metric over time, not just a one-time eval.)
- "Can you ever fully eliminate hallucination?" (No — honest answer given the architecture; you can only reduce likelihood and increase detectability/recoverability. Interviewers are testing for intellectual honesty here as much as technique knowledge.)
- "What's the difference between a hallucination and the model just being wrong because its training data was wrong?" (Worth distinguishing — the former is the model generating unsupported content beyond what any source said; the latter is faithfully reproducing an error that existed in its training data. Different problems, different fixes — the second isn't solvable by better grounding/RAG, only by correcting the source of truth.)

## 5.2 Improving Model Performance

### The decision framework (this is the actual interview content — not a list of techniques, but *when to use which*)

| Approach | Fixes | Cost | When to use |
|---|---|---|---|
| **Prompt engineering** | Format, instruction-following, minor reasoning gaps | Very low | Always try first |
| **RAG** | Missing/outdated knowledge, need for verifiable grounding | Low-medium | When the model lacks *facts* it should have access to |
| **Fine-tuning** | Style, domain-specific behavior, output format consistency, task-specific performance at scale | High (data + compute + eval) | When prompting/RAG plateau and you have volume + labeled data to justify it |
| **RLHF / preference tuning** | Alignment with nuanced human judgment, safety behavior | Very high | Rare for application teams; usually done by model providers, not app builders |
| **Model selection/routing** | Cost/latency/capability trade-offs | Low-medium | Use a smaller/cheaper model for easy queries, larger model for hard ones |

**Key point interviewers probe**: people default to "let's fine-tune" too early. Fine-tuning is expensive, requires quality labeled data, and — critically — **does not reliably teach the model new factual knowledge as well as RAG does**; it's much better suited to teaching *behavior/style/format* than *facts*. A very common wrong answer is "the model doesn't know about our internal docs, let's fine-tune it" when RAG is the correct tool for that specific problem.

**Other performance levers:**
- **Evaluation-driven iteration**: you can't improve what you don't measure — a proper eval set (with real, ideally human-labeled examples) that you run against before/after every change, rather than vibes-based "it seems better."
- **Prompt caching**: reusing computed attention state for repeated prompt prefixes (e.g., a long system prompt reused across many requests) to cut latency/cost — an infrastructure-level lever, not a quality lever, but often grouped into "performance."
- **Model routing/cascading**: send easy queries to a cheap/fast model, escalate to a larger model only when needed (e.g., based on a confidence signal or query classifier) — balances quality and cost at scale.

### Quantization and QLoRA (the efficiency lever)
This is a distinct, concrete technique worth knowing on its own, separate from the decision-framework above — it's about making fine-tuning and self-hosted inference *affordable*, not about choosing whether to fine-tune in the first place.

- **Quantization**: reducing the numerical precision used to store a model's weights — e.g., from 32-bit or 16-bit floating point down to 8-bit or even 4-bit integers. This shrinks memory footprint and speeds up inference substantially, at some cost to accuracy (usually small, if done carefully — techniques like GPTQ and AWQ are specifically designed to minimize the accuracy loss from quantization).
- **Why it matters practically**: it's what makes self-hosting large models on limited hardware feasible at all — a model that needs 140GB of GPU memory at full precision might run in ~35GB at 4-bit quantization, the difference between needing a multi-GPU server and running on a single consumer-grade GPU.
- **QLoRA**: combines two ideas — **LoRA** (Low-Rank Adaptation, a parameter-efficient fine-tuning method that freezes the original model weights and trains only small, low-rank "adapter" matrices injected into the model, drastically reducing the number of trainable parameters and therefore the compute/memory needed to fine-tune) with **quantization** of the frozen base model. The result: you can fine-tune a large model on a single GPU that couldn't even hold the model at full precision, let alone fine-tune it fully — this is specifically what made fine-tuning large open-weight models accessible outside of large labs with big GPU clusters.

### Interview questions you should expect
- "Your model isn't following your formatting instructions reliably. Fine-tune or better prompting?" (Prompting/structured-output APIs first — this is a classic instruction-following gap, cheap to fix without fine-tuning.)
- "Your model doesn't know about your company's internal product catalog. Fine-tune or RAG?" (RAG — this is a knowledge-access problem, and fine-tuning is worse at reliably injecting exact facts and much more expensive to keep current as the catalog changes.)
- "When does fine-tuning actually make sense?" (Consistent domain-specific style/tone at scale, structured task performance where prompting plateaus, or reducing prompt length/cost when a huge few-shot prompt could instead be baked into weights — and only when you have enough quality data to do it well.)
- "How do you know if a change you made actually improved the system, rather than just feeling better on the few examples you tried?" (Eval set discipline — this is the answer interviewers are fishing for, every time.)
- "Why would you quantize a model, and what's the trade-off?" (Memory/cost/latency savings, especially for self-hosted deployment, at the cost of some accuracy — the trade-off is usually favorable at 8-bit and still reasonable at 4-bit with modern quantization methods, but it should be validated against your own eval set, not assumed safe by default.)
- "What problem does LoRA/QLoRA solve that full fine-tuning doesn't?" (Full fine-tuning requires updating and storing every parameter in the model — extremely expensive in compute and memory for large models; LoRA trains a tiny fraction of parameters via low-rank adapters, and QLoRA additionally quantizes the frozen base model, together making fine-tuning large models feasible on far more modest hardware.)

## 5.3 Deploying Generative AI Applications

### What actually matters here (system design territory — your strongest ground given backend experience)

- **Latency management**: LLM calls are slow (hundreds of ms to seconds) relative to typical API latency budgets — streaming responses (token-by-token) is close to mandatory for user-facing chat UX; for backend/agent pipelines, async processing and parallelizing independent LLM calls where possible.
- **Cost management**: token-based pricing means cost scales with both input context size and output length — prompt caching, model routing (cheap model for easy tasks), and context-budget discipline (Layer 1.3) are all cost levers, not just quality levers.
- **Rate limiting & retries**: provider APIs have rate limits and occasional failures — need backoff/retry logic, and ideally multi-provider fallback for critical paths.
- **Observability/tracing**: LLM pipelines are notoriously hard to debug from logs alone — you need full request/response tracing including intermediate steps (retrieved chunks, tool calls, agent reasoning traces), not just final input/output, or you cannot diagnose failures after the fact. Tools like LangSmith, Langfuse, or custom tracing exist specifically for this.
- **Guardrails**: input validation (prompt injection defenses), output validation (PII leakage, toxic content, schema conformance), and business-logic guardrails (the model shouldn't be able to authorize a refund over $X without a separate check) — treat the LLM's output as untrusted the same way you'd treat any external input, not as trusted application logic.
- **Versioning and rollback**: prompts and model versions both need version control and the ability to roll back — a "prompt change" is a production code change and should go through the same rigor (testing, staged rollout) as any other deploy, not be treated as a casual text edit.
- **Evaluation in CI/CD**: automated eval suites that run against a golden test set on every prompt/pipeline change, ideally blocking deploy on regression — treating quality as a testable, gatable property rather than something checked manually and occasionally.

### Interview questions you should expect
- "Design the deployment architecture for a customer-facing RAG chatbot expected to handle 10K requests/day." (This is a full system design question — expect to cover: ingestion pipeline, vector DB choice, API layer, streaming responses, caching strategy, rate limiting, observability, and guardrails — genuinely play to your backend-architecture strength here.)
- "How do you catch a quality regression before it reaches production, given that LLM outputs are non-deterministic?" (Eval suite with a fixed golden set run pre-deploy, LLM-as-judge or rule-based scoring, staged/canary rollout with production monitoring on real traffic, not just pre-deploy testing alone.)
- "Your LLM API provider has an outage. What's your fallback strategy?" (Multi-provider failover if the use case allows model-swapping, graceful degradation — e.g., serve cached/non-AI response — circuit breakers, and clear user-facing error states rather than silent failure.)
- "How do you prevent a prompt injection attack via a retrieved document from causing the agent to take a harmful action?" (Ties back to Layer 1.2 and 4.1 — least-privilege tool access, human confirmation before irreversible actions, treating retrieved/tool content as data not instructions, output validation before any action executes.)

## 5.4 VAD (Voice Activity Detection)

### What it actually is
VAD is a signal-processing/ML component specific to **voice-based AI pipelines** (voice agents, real-time transcription) — it detects when a person is actually speaking versus silence/background noise in an audio stream, so the system knows when to start/stop capturing audio for transcription, and critically, when the user has *finished* speaking (turn-taking) so the agent knows when to respond. This is somewhat orthogonal to the text-based GenAI stack above — relevant specifically if the role touches voice agents/call-center AI (plausible given a travel company like MakeMyTrip could have voice-based booking/support use cases).

**Why it matters for agent design**: bad VAD causes two classic failure modes — the agent interrupts the user mid-sentence (VAD triggered too early on a pause), or the agent has an awkward long delay before responding (VAD too conservative, waiting too long to confirm silence). This is a real UX-critical tuning problem in voice-agent systems, not a minor detail.

### Interview questions you should expect
- "How does VAD fit into a voice agent's pipeline, end to end?" (Audio stream → VAD detects speech segments → speech-to-text on detected segments → LLM processes transcribed text → text-to-speech → playback; VAD specifically gates when STT runs and when the agent considers the user's turn complete.)
- "Your voice agent keeps interrupting users. What's likely wrong?" (VAD end-of-speech threshold tuned too aggressively/short — treating a natural mid-sentence pause as the end of the turn.)
- *(If this doesn't map to your target role's actual scope, it's reasonable to deprioritize deep VAD study — flag this to the interviewer/role context rather than over-investing here.)*

---

---

## 5.5 Temporal Knowledge Graphs (Graphiti)

### What it actually is
A standard knowledge graph is a snapshot — it represents relationships as currently true, with no built-in notion of *when* a fact was true or *when it changed*. A **temporal knowledge graph** adds time as a first-class dimension: edges/facts have validity intervals, so the graph can represent "X worked at Company A from 2020-2023, then Company B from 2023-present" and answer both "where does X work now" and "where did X work in 2021" correctly, without one overwriting the other. **Graphiti** (from Zep) is a specific open-source framework built for this in the context of AI agent memory — it incrementally builds a temporal knowledge graph from conversational/interaction data in real time, explicitly designed so agents can maintain accurate, evolving memory of users/entities over long-running relationships without needing full graph rebuilds and without losing historical facts when new ones arrive.

**Why this matters for agentic systems specifically**: a long-running agent (e.g., a personal assistant used over months) needs memory that updates as facts change ("user's job changed") without simply overwriting old context in a way that breaks reasoning about the past, and without requiring an expensive full re-processing of all history on every update. This is a genuinely different engineering problem than a static RAG knowledge base.

### Interview questions you should expect
- "How is a temporal knowledge graph different from a regular knowledge graph, and why would an agent need one?" (Time-scoped fact validity vs. a static snapshot; needed for agents maintaining memory across long-running relationships where facts genuinely change over time.)
- "How would you handle a user telling your agent something that contradicts an earlier stated fact?" (This is exactly Graphiti's core problem — invalidate/bound the old fact's validity rather than delete it, so the system can still reason about what was true when, while using the current fact going forward.)
- "What's the incremental-update advantage of Graphiti-style temporal graphs over rebuilding a knowledge graph from scratch?" (Real-time, low-latency updates as new information arrives vs. expensive batch reprocessing — critical for agents that need to react to new information immediately, not on a nightly batch job.)

---

## 5.6 Guardrails & Safety

### Why this is treated as its own topic
Multiple current interview breakdowns list "Safety & Security" as a standalone category, distinct from hallucination mitigation (5.1) — the framing worth internalizing is that agent questions are really risk-management questions. Hallucination mitigation is about the *model* getting things right; guardrails are about the *system* containing the damage when it doesn't, or when it's actively attacked. Different failure mode, different toolkit.

### The core guardrail categories

- **Input guardrails**: validating/filtering what reaches the model — prompt injection detection, PII detection before it's sent to a third-party model provider, topic/scope classifiers that reject out-of-domain queries before they're even processed (e.g., a travel-booking bot refusing to engage with medical advice questions).
- **Output guardrails**: validating what the model produces before it's shown to a user or acted on — schema/format validation, toxicity/PII leakage checks, fact-checking claims against retrieved sources (ties to faithfulness checking in 5.1), and topic guardrails that catch the model drifting into out-of-scope territory even if the input guardrail missed it.
- **Action guardrails** (the agent-specific category): before an agent *executes* anything with a real-world side effect — sending an email, making a purchase, modifying a database — validate the proposed action against policy: is this within the agent's allowed scope, does it exceed a cost/risk threshold requiring human approval, is it irreversible. This is the layer that turns "the model wants to do X" into "the system actually lets X happen," and it should never be skipped just because the model sounded confident.
- **Confidence/cost-based routing to humans**: a consistent pattern across production guardrail design — the model proposes a decision, but anything above a confidence or dollar threshold routes to a human, because a wrong auto-approval is expensive. This reframes guardrails from "block bad stuff" to "calibrate autonomy to consequence" — the same principle that shows up in harness engineering (Layer 6.1).
- **Adversarial testing**: guardrails need to be tested the way security controls are tested — deliberately trying to break them (prompt injection attempts, jailbreak attempts, edge-case inputs designed to slip past a classifier) as a standard part of the eval/testing process, not just testing the happy path.

### Interview questions you should expect
- "Design the guardrails for an agent that can issue refunds up to a certain amount autonomously." (Cost-threshold routing — auto-approve below a dollar amount, require human approval above it; input validation on the refund request itself; action-level check that the refund amount and target account match the original transaction, not just that the request "sounds legitimate"; full audit logging for every decision, approved or escalated.)
- "How do you defend against prompt injection in a RAG system where the untrusted content comes from a retrieved document, not the user?" (Ties directly to Layer 1.2 — treat retrieved content as data, not instructions, structurally separate it from system instructions, and add output-level guardrails that catch the agent attempting an action it wasn't asked to take by the actual user.)
- "What's the difference between a guardrail and a hallucination-mitigation technique?" (Mitigation reduces the *likelihood* the model produces bad output; guardrails catch and contain bad output *after* it's produced, regardless of why it happened — including cases that aren't hallucination at all, like a successful prompt injection or a legitimate-but-out-of-policy request. You need both; neither substitutes for the other.)
- "How would you adversarially test your own guardrails before shipping?" (Deliberately craft prompt injection attempts, boundary-condition inputs, and jailbreak-style queries as part of your eval suite — treat it like security testing, run it regularly, not just once before launch.)

---

# LAYER 6 — THE META-SKILL: SHIPPING WITH AI, NOT JUST BUILDING ON IT

This layer is different from everything above — it's not "know this concept," it's "demonstrate this working discipline." This is increasingly what separates senior/staff-level GenAI interview performance from mid-level: not knowing more acronyms, but showing you've internalized *how to work responsibly at the speed AI enables without the speed causing damage*.

## 6.1 Harness Engineering

### What it actually is
A "harness" is the scaffolding *around* an AI system that makes its outputs trustworthy, testable, and safe to act on — evaluation suites, guardrails, verification loops, sandboxed execution environments, structured logging/tracing, and rollback mechanisms. "Harness engineering" is the discipline of building that scaffolding deliberately, as a first-class engineering artifact, rather than treating the AI component as a black box you just call and trust. The core idea: **the AI model's raw capability is necessary but not sufficient — the harness is what makes that capability production-safe.**

**Concrete components of a good harness:**
- An **eval suite** with real test cases and pass/fail (or scored) criteria, run automatically on every change (ties to 5.3's CI/CD eval discipline).
- **Sandboxing** for any AI-executed action with side effects (code execution, file changes, API calls) — run in an isolated environment where failure is contained, before anything touches production.
- **Verification loops** — a step, ideally automated/programmatic rather than another LLM call, that checks the AI's output actually satisfies the requirement (tests pass, output matches schema, referenced facts exist) before accepting it.
- **Human checkpoints** calibrated to the cost of being wrong — cheap/reversible actions can be fully autonomous; expensive/irreversible ones need a human gate.
- **Observability** — you must be able to see *why* the AI did what it did (reasoning trace, tool calls, intermediate state), not just the final output, to debug failures.

### Interview questions you should expect
- "What does 'harness engineering' mean to you, and why does it matter more as AI models get more capable?" (More capable models can take more consequential actions autonomously — the harness is what bounds the blast radius of a wrong action; capability without a harness is a liability, not a pure win.)
- "You're using an AI coding agent to autonomously make changes to a production codebase. What harness would you build around it before trusting it?" (Sandboxed execution, full test suite gating any merge, diff review (human or automated), rollback capability, and scoped permissions — the agent shouldn't have more access than the task strictly requires.)
- "How do you decide which AI actions need a human-in-the-loop checkpoint and which can be fully autonomous?" (Cost/reversibility of a wrong action — a formatting suggestion is cheap to be wrong about; a production deploy or a financial transaction is not; calibrate autonomy to consequence, not to how well the model has performed historically.)

## 6.2 AI Debugging (locating/diagnosing/patching bugs in large legacy repos)

### What this actually tests
Using AI to debug a "massive, messy legacy repo" is a different skill than using AI to write greenfield code. The core challenges are: the codebase is too large to fit in any context window, historical context (why was it written this way) often isn't documented anywhere the AI can see, and a wrong fix can silently break something far away in the codebase that isn't obviously connected. Interviewers are testing whether you'll use AI as a *reckless shortcut* or as a *force multiplier with the right constraints*.

**Effective approach (this is what a strong answer sounds like):**
- **Narrow scope before generating**: use AI to help *locate* the relevant code (search/grep-assisted, trace the error/stack trace back through call sites) before asking it to *change* anything — diagnosis and treatment are separate steps, don't let the model skip straight to a patch on a codebase it doesn't fully see.
- **Reproduce first**: get a reliable, minimal repro (a failing test) before any fix — this is true with or without AI, but AI makes it tempting to skip because it can *propose* plausible-looking fixes without ever confirming they address the actual failure.
- **Constrain the blast radius**: ask for the smallest possible diff, not a rewrite — legacy code often has undocumented behavior that a "cleaner" rewrite silently breaks.
- **Verify against tests, not against the AI's own explanation**: an AI confidently explaining why its fix works is not evidence the fix works — the test suite (or a new test written for this specific bug) is the actual evidence.
- **Use AI for the parts it's actually good at**: pattern-matching across a large search space (finding all call sites of a function, spotting similar past bugs), summarizing unfamiliar code sections, generating hypotheses to check — not for confidently declaring "this is the bug" without verification.

### Interview questions you should expect
- "Walk me through how you'd use AI to debug a production issue in a 500K-line legacy codebase you've never seen before." (Expect: reproduce first, use AI to help navigate/summarize rather than guess, narrow to the smallest relevant scope, verify any proposed fix against tests before trusting it, and be explicit that AI's explanation of *why* something is broken is a hypothesis to verify, not a conclusion.)
- "An AI coding assistant confidently tells you it found and fixed the bug. How do you verify that before merging?" (Test suite verification, ideally a test that specifically reproduces the original failure and now passes; don't accept the AI's own narrative of correctness as sufficient evidence.)
- "What's a risk specific to using AI on legacy code, versus new code?" (Undocumented implicit behavior/business logic that isn't visible in the code the AI can see — the AI can produce a change that's locally correct but breaks an invisible dependency; this is exactly why blast-radius discipline matters more here than in greenfield work.)

## 6.3 AI System Design (architecting while using AI to pressure-test the design)

### What this actually tests
This isn't "design a system" and it isn't "use AI to design a system for you" — it's demonstrating that you can use AI as a genuine **thinking partner for trade-off analysis** without outsourcing the judgment calls that require context the AI doesn't have (your actual constraints, team, scale, cost sensitivity, org politics). A senior engineer who says "I asked the AI and it said microservices" has failed this evaluation; one who says "I used AI to rapidly draft three interface options and enumerate edge cases I might've missed, then made the call myself based on our actual latency/team-size constraints" has passed it.

**What a strong workflow looks like:**
- Use AI to **rapidly enumerate options and trade-offs** you might not have thought of — breadth, fast.
- Use AI to **draft interface/API contracts** quickly so you can react to something concrete rather than staring at a blank page.
- Use AI to **pressure-test your own design** — explicitly ask it to find edge cases, failure modes, and scaling limits in a design you've proposed, adversarially.
- **You** own the final trade-off decision, because it requires context (team skill, existing infra, actual traffic patterns, organizational constraints) the AI doesn't have and can't verify.
- Be explicit in interviews about *where* you'd loop in AI in your actual design process versus where you wouldn't — this demonstrates you have an actual methodology, not just "I use AI a lot."

### Interview questions you should expect
- "How would you use AI while designing a new system, without just accepting whatever it proposes?" (Use it for breadth of options and adversarial edge-case pressure-testing, not as the final decision-maker; the decision requires context — team, cost constraints, existing systems — the AI doesn't have.)
- "AI-generated a system design that looks clean and well-reasoned. What do you personally verify before committing to it?" (Whether it accounts for your actual scale/traffic, whether it fits your team's operational capability to run it, whether the "clean" design is hiding complexity it pushed into a component the AI didn't examine deeply, and whether trade-offs are stated honestly or the design is just confidently one-sided.)
- "Design a RAG-based customer support system, and tell me where in this process you'd use AI to help versus where you wouldn't." (This combines Layer 2/4/5 technical content with the meta-skill — a strong answer shows both.)

## 6.4 Shipping With AI Without Hallucinating Production Down

### The actual discipline being tested
This is the synthesis of everything above: AI-assisted development can move fast, and "fast" without discipline means shipping confidently-wrong code, configs, or content at a pace that outstrips your ability to catch it. The core failure mode isn't "AI wrote bad code" — it's **trusting AI output at the same confidence level you'd trust verified, tested human work**, when AI output hasn't earned that trust yet on this specific task.

**Principles that should show up in your answer, consistently:**
- **AI output is a draft/hypothesis, not a deliverable**, until verified by something outside the AI itself (tests, a second independent check, actual execution against real data).
- **Verification cost should scale with consequence** — a variable rename doesn't need the scrutiny a database migration or auth-logic change does; calibrate review depth to blast radius, same principle as harness engineering (6.1).
- **Never let AI-generated code/config touch production without the same gates as human-written code** — code review, tests, staged rollout — "AI wrote it" is not a reason to skip your existing engineering discipline, arguably it's a reason to be *more* rigorous, not less, until you've built calibrated trust in a specific tool for a specific task class.
- **Watch for confident-sounding wrongness specifically** — AI failure mode is rarely "obviously broken," it's "plausible and wrong," which is exactly the kind of error that slips past a rushed review because it *looks* right.
- **Keep a human accountable for the decision to ship**, even in highly AI-assisted workflows — "the AI said it was fine" is never an acceptable postmortem answer.

### Interview questions you should expect
- "You're under deadline pressure and an AI coding assistant says a change is ready to ship. Walk me through what happens before it actually ships." (Tests/CI gate, code review (human or rigorous automated check) regardless of source, staged rollout with monitoring if the change is significant, and explicit acknowledgment that deadline pressure is exactly the condition under which people skip steps and get burned — a strong answer names that risk directly rather than pretending pressure doesn't affect behavior.)
- "How do you calibrate how much you trust an AI coding agent over time, for a given task type?" (Track its actual track record on that specific task category via your own verification, not vibes — trust should be earned per-task-type based on observed accuracy, not extended uniformly because it did well once on something else.)
- "Tell me about a time (or hypothetically, how you'd handle it) when AI-generated content/code looked correct but wasn't, and how you'd design your process to catch that class of error going forward." (Wants a concrete, non-generic answer — specific verification step you'd add, not just "be more careful.")

---

# APPENDIX

## Flagged for clarification: "Open Knowledge Format"
This term is ambiguous as stated — it could refer to several different things depending on context:
- **OWL/RDF** (Web Ontology Language / Resource Description Framework) — W3C standards for representing knowledge graphs in an interoperable, formal way (relevant if the role touches semantic web / formal ontology work).
- A specific company/product's internal term for their knowledge export format (common in interview-prep lists that get passed around informally — sometimes these are role-specific jargon from the company doing the interviewing).
- Open standards for LLM-consumable knowledge bases (an emerging, less standardized space as of your training cutoff).

**Recommendation**: if this term came from a specific job posting or interviewer, it's worth asking them directly what they mean — guessing wrong here wastes prep time on the wrong thing.

## Deprioritized: AGI
Artificial General Intelligence is a research/philosophy topic, not an implementable system you'll be asked to design. If it comes up, it'll almost certainly be a brief opinion/discussion question ("do you think we're close to AGI," "how would you define it"), not a technical deep-dive. Have a grounded, honest point of view (e.g., current systems are narrow/lack persistent learning and genuine world-models despite fluency — this is a defensible, mainstream technical position) but don't spend real study time here relative to everything else on this list.

## The one project you should actually build
Every current interview breakdown of this space converges on the same point: a small but complete agent you can walk through end-to-end beats naming many frameworks or reciting definitions. Theory alone caps how well you can answer follow-up questions, because interviewers probe implementation details ("what happened when the tool call failed," "how did you decide chunk size") that are very hard to fake convincingly without having actually hit them.

**A scoped project that touches most of this doc**: a RAG-powered assistant over a small document set (even something like your own resume + a few technical articles), with:
- Proper chunking (pick one strategy deliberately, be able to justify it)
- Hybrid search + reranking (Layers 2.2–2.3)
- 2-3 real tools (e.g., search the knowledge base, call one external API, run a simple calculation)
- Built as an actual agent loop in LangGraph (Layer 3.2/4.1), not a single fixed chain
- Basic memory (conversation state at minimum)
- At least one guardrail (e.g., a human-confirmation step before any tool with a side effect)
- A small eval set — even 10-15 test queries with expected behavior — that you run before/after changes

Deployed and put on GitHub, even minimally. Being able to say "here's a specific bug I hit and how I fixed it" is worth more in an interview than fluency across every topic in this document — it's the difference between reciting Layer 4's failure modes and having actually watched an agent loop forever until you fixed it yourself.

---

# SUGGESTED STUDY SEQUENCE

1. **Layer 1 fully** — this is the foundation everything else is built on; rushing this creates gaps that show up everywhere later.
2. **Layer 2.1–2.5** (Chunking → Vector DB → Reranking → Graph DB → RAG) — build a mental model of the standard pipeline, including the retrieve-then-rerank pattern, before the advanced variants.
3. **Layer 2.6–2.8** (KAG, RAPTOR, Agentic RAG) — these will click fast once 2.1–2.5 are solid; they're each a specific fix to a specific RAG limitation.
4. **Layer 3** — lighter effort on 3.1–3.3 (focus on concepts over exact APIs unless the role is Python/LangChain-heavy); don't skip 3.4 (MCP/A2A) even though it's new to you — it's increasingly asked as a direct, standalone question, not just background context.
5. **Layer 4** — agentic concepts; this is where a lot of current interview energy is concentrated, don't rush it.
6. **Layer 5** — production concerns; this is your natural strength given backend experience — lean into system-design-style answers here, and don't treat 5.6 (Guardrails) as an afterthought — it's frequently its own interview category, not a subset of hallucination discussion.
7. **Layer 6** — the meta-skill layer; honestly, you can start forming opinions on this *now*, in parallel with everything else, since it's about judgment and process more than facts to memorize.
8. **In parallel with all of the above, start the one project** (see above) as early as you reasonably can — it's what turns the rest of this document from recitable facts into defensible experience.

If useful, next step could be building a set of practice questions/flashcards from this doc, or going deep on a specific layer with worked examples (e.g., actually sketching a RAG system architecture end to end, or writing a basic LangGraph agent loop).

