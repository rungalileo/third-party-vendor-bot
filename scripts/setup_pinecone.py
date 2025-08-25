"""
This script sets up a Pinecone index for storing and retrieving company directory documents using the documents in the `company_directory` folder.

To use this, you will need to have the following environment variables set in the .env file:
- `PINECONE_API_KEY`: Your Pinecone API key.
- `OPENAI_API_KEY`: Your OpenAI API key (for embeddings).
- `PINECONE_INDEX_NAME`: Your Pinecone index name.
"""

import asyncio
import os

from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from pinecone import Pinecone

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable not set")

if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME environment variable not set")

# Initialize OpenAI embeddings to match the model used in rag_tool.py
EMBEDDINGS = OpenAIEmbeddings(model="text-embedding-3-large")


def load_documents(path):
    """Load all markdown and text documents from company directory"""
    documents = []
    
    # Load markdown files
    md_loader = DirectoryLoader(path, glob="*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    md_documents = md_loader.load()
    documents.extend(md_documents)
    
    # Load text files  
    txt_loader = DirectoryLoader(path, glob="*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    txt_documents = txt_loader.load()
    documents.extend(txt_documents)
    
    print(f"Loaded {len(md_documents)} markdown files and {len(txt_documents)} text files")
    return documents


def chunk_documents(documents):
    """Chunk documents semantically using headers and other separators"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=[
            "\n## ",  # Header 2 (primary separator for company profiles)
            "\n### ", # Header 3 
            "\n\n",   # Double newlines (paragraphs)
            "\n",     # Single newlines
            " ",      # Spaces
            ".",      # Sentences
            ",",      # Clauses
            "\u200b", # Zero-width space
            "\uff0c", # Fullwidth comma
            "\u3001", # Ideographic comma
            "\uff0e", # Fullwidth full stop
            "\u3002", # Ideographic full stop
            "",       # Character-level
        ],
        is_separator_regex=False,
    )

    chunked_docs = text_splitter.split_documents(documents)
    
    # Add the required "text" field to metadata for compatibility
    for doc in chunked_docs:
        doc.metadata["text"] = doc.page_content
    
    return chunked_docs


def setup_pinecone_index(index_name: str) -> None:
    """Initialize Pinecone and create/connect to index"""
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if index exists, create if not
    if index_name not in pc.list_indexes().names():
        print(f"Creating new index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=3072,  # text-embedding-3-large dimensions
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
        )
    else:
        print(f"Index {index_name} already exists")


def check_index_has_data(index, namespace: str = "") -> bool:
    """Check if the index already contains data in the specified namespace"""
    try:
        stats = index.describe_index_stats()
        if namespace:
            # Check specific namespace
            namespaces = stats.get("namespaces", {})
            namespace_stats = namespaces.get(namespace, {})
            vector_count = namespace_stats.get("vector_count", 0)
        else:
            # Check total vector count
            vector_count = stats.get("total_vector_count", 0)
        return vector_count > 0
    except Exception as e:
        print(f"Error checking index stats: {e}")
        return False


def upload_to_pinecone(chunked_docs, index_name: str, namespace: str = "", force_upload: bool = False) -> PineconeVectorStore:
    """Upload chunked documents to Pinecone"""

    # Check if index has data and we're not forcing upload
    if not force_upload:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(index_name)

        if check_index_has_data(index, namespace):
            print(f"Index {index_name} already contains data in namespace '{namespace}'. Skipping upload.")
            print("Use force_upload=True to overwrite existing data.")
            return PineconeVectorStore(index_name=index_name, embedding=EMBEDDINGS, namespace=namespace)

    # Create vector store and upload with namespace
    print(f"Uploading {len(chunked_docs)} chunks to Pinecone with namespace '{namespace}'...")
    vector_store = PineconeVectorStore.from_documents(
        documents=chunked_docs, 
        embedding=EMBEDDINGS, 
        index_name=index_name,
        namespace=namespace
    )

    print(f"Successfully uploaded {len(chunked_docs)} document chunks to Pinecone namespace '{namespace}'")
    return vector_store


def test_retrieval(index_name: str, query: str, namespace: str = ""):
    """Test document retrieval from Pinecone"""
    vector_store = PineconeVectorStore(index_name=index_name, embedding=EMBEDDINGS, namespace=namespace)

    # Test similarity search
    results = vector_store.similarity_search(query, k=3)

    print(f"\nTest query: '{query}' in namespace '{namespace}'")
    print(f"Found {len(results)} relevant chunks:")
    for i, doc in enumerate(results, 1):
        print(f"\n{i}. {doc.page_content[:200]}...")
        print(f"   Source: {doc.metadata.get('source', 'Unknown')}")


company_documents = [
    {
        "index_name": PINECONE_INDEX_NAME,
        "path": "company_directory",
        "test_query": "security consulting services",
        "namespace": "company-directory"
    }
]


async def main():
    """
    Main function to process and upload documents asynchronously
    """

    for doc in company_documents:
        index_name = doc["index_name"]
        path = doc["path"]
        test_query = doc["test_query"]
        namespace = doc.get("namespace", "company-directory")

        print(f"Loading documents from {path} folder...")
        loaded_documents = load_documents(path)
        print(f"Loaded {len(loaded_documents)} documents")

        print(f"Chunking documents for {index_name}...")
        chunked_docs = chunk_documents(loaded_documents)
        print(f"Created {len(chunked_docs)} chunks")

        print(f"Setting up Pinecone index {index_name}...")
        setup_pinecone_index(index_name)

        # Only upload if index is new or doesn't have data
        print(f"Uploading to Pinecone {index_name} with namespace {namespace}...")
        _ = upload_to_pinecone(chunked_docs, index_name=index_name, namespace=namespace)

    # Wait for Pinecone to index the data
    print("Waiting for Pinecone to index the data...")
    await asyncio.sleep(10)

    # Test retrieval for each index
    for doc in company_documents:
        index_name = doc["index_name"]
        test_query = doc["test_query"]
        namespace = doc.get("namespace", "")
        print(f"Testing retrieval for {index_name} with query: '{test_query}'")
        test_retrieval(index_name=index_name, query=test_query, namespace=namespace)

    print("✅ Document processing and upload complete!")


if __name__ == "__main__":
    asyncio.run(main())
