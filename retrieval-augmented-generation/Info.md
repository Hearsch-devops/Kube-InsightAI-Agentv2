This is the RAG folder
kube-insight-ai/
└── rag/
    └── documents/
        ├── kubernetes/
        ├── jenkins/
        ├── gitlab/
        ├── docker/
        └── terraform/
        └── linux/
------------------------------------------
Use this single command:
cat > retrieval-augmented-generation/Info.md <<'EOF'
# Kube-InsightAI — RAG

## 1. Setup
Create and activate the virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
2. Install Dependencies
pip install chromadb openai python-dotenv httpx
3. Configure Environment
Create .env in the repository root with LLMFOUNDRY_TOKEN and PROJECT_NAME.
 Never commit .env.
4. Build ChromaDB
After cloning/forking, create the local vector database:
cd retrieval-augmented-generation
python -m rag.vector_store
5. Run RAG Pipeline
Run the complete RAG system:
python -m rag.pipeline
6. Test Document Loader
Load and verify Kubernetes documents:
python -m rag.document_loader
7. Test Text Splitter
Test hybrid chunking:
python -m rag.text_splitter
Current configuration: 1000-character chunks with 200-character overlap.
8. Test Embeddings
Generate/test embeddings:
python -m rag.embeddings
Embedding model: models/gemini-embedding-001 (3072 dimensions).
9. Test Vector Store
Create/rebuild ChromaDB:
python -m rag.vector_store
Current collection: kubernetes_docs with 418 chunks.
10. Test Retriever
Test similarity retrieval:
python -m rag.retriever
Current configuration: Top-K = 5, distance threshold = 0.70.
11. Run Complete Pipeline
python -m rag.pipeline
Flow: Query → Retrieval → Context → Prompt → Gemini 2.5 Flash → Answer.
12. Important Python Rule
Run modules from retrieval-augmented-generation/ using python -m rag.<module>.
 Example: python -m rag.pipeline instead of python rag/pipeline.py.
13. ChromaDB Rule
chroma_db/ is generated locally and is not committed to Git.
 If deleted, recreate it with python -m rag.vector_store.
14. Knowledge Base
Kubernetes documents are stored under:
knowledge_base/kubernetes/
If documents change, rebuild ChromaDB.
15. Experiments
exp-a-basic        → Basic chunking
exp-b-structure    → Structure-aware chunking
exp-c-hybrid       → Hybrid chunking
exp-d-mmr          → MMR retrieval
exp-e-llm-reranking → LLM reranking
16. RAG Architecture
Documents → Loader → Chunking → Embeddings → ChromaDB
→ Retriever → Context → LLM → Grounded Answer
17. RAG vs MCP
RAG provides knowledge from documents; MCP provides access to live systems and tools.
18. Git Rules
Do not commit .env, .venv/, __pycache__/, or chroma_db/.
 Commit source code, knowledge-base documents, experiments, and documentation.
19. Current Status
Manual RAG core is complete.
 Next: LangChain → LangGraph → MCP → LLMOps.
 EOF

Then simply verify:

```bash
cat retrieval-augmented-generation/Info.md
This version is much better as a quick reference/runbook rather than a long theory document. 🚀

