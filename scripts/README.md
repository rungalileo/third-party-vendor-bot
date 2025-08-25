# RAG System Setup

This directory contains scripts to set up and manage the RAG (Retrieval-Augmented Generation) system for the third-party vendor bot.

## Setup Process

### 1. Environment Variables

First, ensure you have the following environment variables set in your `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=your_pinecone_index_name_here
```

### 2. Load Documents into Pinecone

Run the setup script to load company directory documents into Pinecone:

```bash
# From the project root directory
python scripts/setup_pinecone.py
```

This script will:
- Load all markdown and text files from the `company_directory` folder
- Chunk the documents using semantic separators (headers, paragraphs)
- Create a Pinecone serverless index (if it doesn't exist) with 3072 dimensions for text-embedding-3-large
- Upload the document embeddings to Pinecone using the "company-directory" namespace
- Test the retrieval functionality with a sample query

### 3. Use the RAG System

After running the setup script, your application can use the RAG system without loading documents each time:

```python
from rag_tool import get_rag_system

# Create RAG system instance (uses existing vectors)
rag_system = get_rag_system(
    index_name=None,  # Uses PINECONE_INDEX_NAME from environment
    namespace="company-directory",
    description="Company Directory Knowledge Base"
)

# Search the knowledge base
response = rag_system.search("What security consulting services are available?")
print(response)
```

