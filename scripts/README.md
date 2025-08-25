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
cd scripts
python setup_pinecone.py
```

This script will:
- Load all markdown files from the `company_directory` folder
- Chunk the documents appropriately
- Create a Pinecone index (if it doesn't exist)
- Upload the document embeddings to Pinecone
- Test the retrieval functionality

### 3. Use the RAG System

After running the setup script, your application can use the RAG system without loading documents each time:

```python
from rag_tool import get_rag_system

# Create RAG system instance (uses existing vectors)
rag_system = get_rag_system(
    namespace="company-directory",
    description="Company Directory Knowledge Base"
)

# Search the knowledge base
response = rag_system.search("What security consulting services are available?")
print(response)
```

## Key Changes

The updated RAG system:
- **No longer loads documents each time**: Documents are pre-loaded into Pinecone
- **Uses environment variables**: `PINECONE_INDEX_NAME` specifies which index to use
- **Faster initialization**: No document processing during runtime
- **Better resource management**: Avoids crowding the vector database with duplicate embeddings

## Testing

You can test the setup using the provided test script:

```bash
python test_rag_system.py
```

This will verify that the RAG system can connect to the existing vectors and retrieve relevant information.
