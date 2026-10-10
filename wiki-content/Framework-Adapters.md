# Framework Adapters

SLM ships nine small Python packages that plug it into agent frameworks as their native memory or chat-history store. Use one when you are writing code against LangGraph, LangChain, CrewAI or another framework and want that framework's memory to land in SLM, where you can also recall it from the CLI, an MCP client or the dashboard. Only three of the nine are on PyPI today (LangChain, LlamaIndex and CrewAI). The other six install from a clone of the repository. If you only want an AI tool such as Cursor or Claude Code to use SLM, you do not need any of this; see [IDE Setup](IDE-Setup).

## What they are

Each adapter lives in its own folder under `ide/integrations/` in the repository, outside the main `src/` tree, with its own `pyproject.toml`, README and tests. All nine require Python 3.12 to 3.14 and SuperLocalMemory installed in the same environment (`superlocalmemory>=3.6.23,<5`). Platform support follows SLM itself: Apple Silicon macOS, 64-bit Windows and 64-bit Linux.

| Framework | Package | On PyPI | Folder | Implements | Main class |
|---|---|:---:|---|---|---|
| LangChain | `langchain-superlocalmemory` | yes | `langchain` | `BaseChatMessageHistory` | `SuperLocalMemoryChatMessageHistory` |
| LlamaIndex | `llama-index-storage-chat-store-superlocalmemory` | yes | `llamaindex` | `BaseChatStore` | `SuperLocalMemoryChatStore` |
| CrewAI | `crewai-superlocalmemory` | yes | `crewai` | `StorageBackend` | `SuperLocalMemoryBackend` |
| LangGraph | `langgraph-superlocalmemory` | no | `langgraph` | `BaseStore` | `SuperLocalMemoryStore` |
| Semantic Kernel | `semantic-kernel-superlocalmemory` | no | `semantic-kernel` | `VectorStore` and `VectorStoreCollection` | `SuperLocalMemoryVectorStore` |
| Microsoft Agent Framework | `agent-framework-superlocalmemory` | no | `agent-framework` | `ContextProvider`, `HistoryProvider` | `SuperLocalMemoryContextProvider`, `SuperLocalMemoryHistoryProvider` |
| AutoGen | `autogen-superlocalmemory` | no | `autogen` | `Memory` | `SuperLocalMemoryMemory` |
| Google ADK | `google-adk-superlocalmemory` | no | `google-adk` | `BaseMemoryService` | `SuperLocalMemoryService` |
| OpenAI Agents | `openai-agents-superlocalmemory` | no | `openai-agents` | `SessionABC` | `SLMSession` |

The "On PyPI" column was checked against the PyPI JSON endpoint for each package name on 2026-10-11; the six marked "no" returned 404. It will change as packages are published, so check before relying on it. Minimum framework versions from each `pyproject.toml`: `langgraph>=1.0.0`, `semantic-kernel>=1.34.0`, `agent-framework-core>=1.5.0`, `langchain-core>=1.0.0`, `llama-index-core>=0.13.0,<0.15`, `crewai>=1.14.6`, `autogen-agentchat>=0.7.5`, `google-adk>=2.5.0`, `openai-agents>=0.18.3`.

## Installing

For the three published adapters, install next to SLM:

```bash
pip install superlocalmemory langchain-superlocalmemory
```

For the other six, a plain `pip install <name>` fails, so install from the repository folder:

```bash
git clone https://github.com/qualixar/superlocalmemory
pip install ./superlocalmemory/ide/integrations/langgraph
```

Two older single-file adapters, `integrations/langchain_memory.py` and `integrations/crewai_memory.py`, remain at the repository root for backward compatibility. The LangChain one carries a migration notice pointing to the partner package; use the packages above for new work.

## How they store data

All nine follow the same pattern. The adapter opens its own in-process SLM memory engine in Mode A (no language model) on the database at `~/.superlocalmemory/memory.db`, or the path you pass as `db_path=`, with forgetting turned off and the cross-encoder reranker skipped. Content goes in through the engine's normal store call, so SLM's ingestion makes it searchable; the original payload is kept as the exact record, which is what lets a chat history round-trip losslessly. Each adapter tags its records with a session identifier so one conversation, store key or agent never mixes with another. Because the engine runs inside your Python process, async frameworks call it through `asyncio.to_thread` and are not blocked.

Two consequences follow. A record written through an adapter shows up in `slm recall`, over MCP and on the dashboard like any other memory. And because the adapter does not go through the resident daemon, heavy concurrent writing from several processes to one database is something to test in your own setup; the daemon is otherwise the single writer ([Architecture](Architecture)). Optional SLM features such as a cloud provider, backup or connectors keep their own, separately documented network behaviour.

## Per-adapter notes

**LangChain.** Implements `BaseChatMessageHistory`. Records are tagged `langchain:session:<id>`, so each `session_id` is independent. All standard message types are supported and `additional_kwargs` round-trip.

```python
from langchain_core.messages import HumanMessage
from langchain_superlocalmemory import SuperLocalMemoryChatMessageHistory

history = SuperLocalMemoryChatMessageHistory(session_id="my-chat-session")
history.add_messages([HumanMessage(content="What is SLM?")])
print(history.messages)
history.clear()
```

**LlamaIndex.** Implements `BaseChatStore`, for use with `ChatMemoryBuffer`. The session identifier is `llamaindex:` plus a hash of the chat-store key. Import path: `llama_index.storage.chat_store.superlocalmemory`.

**CrewAI.** Implements `StorageBackend` for scope-aware memory records. CrewAI supplies the embeddings; the adapter stores them and ranks by cosine similarity in plain Python. Each `MemoryRecord` is one SLM memory with session `crewai-rec:<id>`. Scope matching is hierarchical (`/project` matches `/project/alpha`, never `/projectx`), and `metadata_filter` supports equality only.

**LangGraph.** Implements `BaseStore` for namespaced long-term memory, usable as `store=` in `create_react_agent` or `StateGraph(...).compile(store=store)`. Search is namespace-prefix plus `filter` matching and returns `score=None`; vector queries are not indexed here, so use SLM's recall for semantic ranking. TTL is not supported, and `"*"` wildcard namespace paths are treated literally.

**Semantic Kernel.** `SuperLocalMemoryVectorStore.get_collection(...)` returns a collection with upsert, get, delete and lifecycle calls. Search is field-filter retrieval with `score=None`; dense-vector ranking is listed as a follow-up. The Semantic Kernel vector-store API is still marked preview, so validate against your installed version.

**Microsoft Agent Framework.** A history provider (`get_messages` and `save_messages` per session) and a context provider whose `before_run` injects recent session memory as instructions and whose `after_run` persists the turn. `max_recall` (default 10) limits how much is injected. Wider semantic recall across the store is a documented follow-up. Do not confuse it with AutoGen; they are separate products.

**AutoGen.** Implements `autogen_core.memory.Memory`. Each `add()` writes a row with an `autogen-mem:` session, and `clear()` deletes only those rows, leaving your other SLM memories alone.

**Google ADK.** Implements `BaseMemoryService`. `add_session_to_memory` is an idempotent upsert per session, and `search_memory` uses SLM recall with post-filtering by app and user. The ranking score is not exposed in the response, and very short event text (under about 15 characters) may not produce searchable facts, though it is still stored.

**OpenAI Agents.** `SLMSession` implements `SessionABC` for ordered conversation history, with deterministic ordering by creation time then row id. Pass `db_path=` to use another database.

## Limits worth knowing

Semantic ranking is not built into the LangGraph and Semantic Kernel adapters; both filter by fields and namespaces. CrewAI is limited to equality metadata filters and in-process cosine ranking, which is fine for modest collections. Six of nine are not yet installable from PyPI. The Python version range is tight (3.12 to 3.14) because it tracks SLM. Detailed behaviour and extra examples are in each adapter's README, and the table of contract status per host is in `ide/integration-contracts.json`.

The dashboard's Bounded Loops pane lists these same nine adapters beside "Any MCP-compatible agent", because loops and the adapters are both ways to put SLM under agent code ([Bounded Loops](Bounded-Loops), [Dashboard Tour](Dashboard-Tour)).

Code: `ide/integrations/<framework>/` (each with a `_v3_*` store module over the SLM engine), `ide/integration-contracts.json`, `docs/framework-adapters.md`.
