import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

load_dotenv()

# Reduce logging noise
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# Define RAG response type similar to your example
class RagResponse:
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents

class RAGSystem:
    def __init__(
        self,
        index_name: str = None,
        namespace: str = None,
        description: str = "Knowledge base",
    ):
        """
        Initialize a RAG (Retrieval-Augmented Generation) system using Pinecone directly.

        Args:
            index_name: Pinecone index name (required)
            namespace: Pinecone namespace (required)
            description: Description of the knowledge base
        """
        if not index_name:
            # Try to get from environment variable
            index_name = os.getenv("PINECONE_INDEX_NAME")
            if not index_name:
                raise ValueError("index_name must be provided or PINECONE_INDEX_NAME environment variable must be set")
        
        if not namespace:
            raise ValueError("namespace must be provided")
        
        self.index_name = index_name
        self.namespace = namespace
        self.description = description
        self._initialized = False
        self.openai_client = None
        self.pc = None
        self.index = None

    def initialize(self):
        """Initialize the RAG system to use existing Pinecone index"""
        if self._initialized:
            return

        try:
            # Initialize OpenAI client
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            self.openai_client = OpenAI(api_key=openai_api_key)

            # Initialize Pinecone
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if not pinecone_api_key:
                raise ValueError("PINECONE_API_KEY environment variable is required")
            
            self.pc = Pinecone(
                api_key=pinecone_api_key,
                spec=ServerlessSpec(cloud="aws", region="us-west-2")
            )
            
            # Connect to existing index
            self.index = self.pc.Index(self.index_name)
            print(f"[INDEX] Connected to existing index '{self.index_name}'")

            self._initialized = True
            print(f"✅ {self.description} RAG initialized successfully (using existing vectors)")

        except Exception as e:
            print(f"❌ Error initializing {self.description} RAG: {e}")
            import traceback
            traceback.print_exc()
            self._initialized = False

    def get_rag_response(self, query: str, top_k: int = 4, galileo_logger=None) -> Optional[RagResponse]:
        """Get RAG response using Pinecone vector store, similar to your example."""
        import time
        start_time = time.time()
        
        # Lazy initialization - only initialize when first used
        if not self._initialized:
            self.initialize()

        if not self._initialized:
            print(f"❌ {self.description} RAG system not initialized")
            return None

        try:
            print(f"[RAG] Making RAG request - Query: {query}, Top K: {top_k}")
            
            # Get embeddings for the query
            embedding_response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Query Pinecone
            query_response = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=self.namespace if self.namespace and self.namespace != "" else None,
                include_metadata=True
            )
            
            # Process results
            if not query_response.matches:
                print("❌ No matches found in Pinecone")
                # Log empty retrieval to Galileo if available
                if galileo_logger:
                    try:
                        galileo_logger.add_retriever_span(
                            input=query,
                            output=[],
                            name="RAG Retriever",
                            duration_ns=int((time.time() - start_time) * 1000000),
                            metadata={
                                "document_count": "0",
                                "namespace": self.namespace,
                                "top_k": str(top_k),
                                "index_name": self.index_name
                            }
                        )
                    except Exception as e:
                        print(f"Failed to log empty retrieval to Galileo: {e}")
                return None
                
            print(f"✅ Found {len(query_response.matches)} matches in Pinecone")
            
            # Format documents
            documents = [
                {
                    "content": match.metadata.get("text", ""),
                    "metadata": {
                        "score": match.score,
                        **match.metadata  # Include all metadata fields
                    }
                }
                for match in query_response.matches
            ]
            
            # Log successful retrieval to Galileo if available
            if galileo_logger:
                try:
                    galileo_logger.add_retriever_span(
                        input=query,
                        output=[doc['content'] for doc in documents],
                        name="RAG Retriever",
                        duration_ns=int((time.time() - start_time) * 1000000),
                        metadata={
                            "document_count": str(len(documents)),
                            "namespace": self.namespace,
                            "top_k": str(top_k),
                            "index_name": self.index_name,
                            "scores": str([doc['metadata']['score'] for doc in documents])
                        }
                    )
                except Exception as e:
                    print(f"Failed to log retrieval to Galileo: {e}")
            
            return RagResponse(documents=documents)
            
        except Exception as e:
            print(f"❌ Error in RAG request: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Log error to Galileo if available
            if galileo_logger:
                try:
                    galileo_logger.add_retriever_span(
                        input=query,
                        output=[],
                        name="RAG Retriever",
                        duration_ns=int((time.time() - start_time) * 1000000),
                        metadata={
                            "document_count": "0",
                            "namespace": self.namespace,
                            "top_k": str(top_k),
                            "index_name": self.index_name,
                            "error": str(e)
                        }
                    )
                except Exception as galileo_e:
                    print(f"Failed to log error retrieval to Galileo: {galileo_e}")
            
            return None

    def search(self, query: str, galileo_logger=None) -> str:
        """Search the configured knowledge base and return a formatted response"""
        rag_response = self.get_rag_response(query, galileo_logger=galileo_logger)
        
        if not rag_response or not rag_response.documents:
            return f"No relevant information found for: {query}"
        
        # Create context from documents
        context = "\n\n".join(doc['content'] for doc in rag_response.documents)
        
        # For now, just return the context directly
        # In the future, you could add LLM summarization here if needed
        return context


# Global cache for RAG instances
_rag_cache = {}


def get_rag_system(
    index_name: str = None,
    namespace: str = None,
    description: str = "Knowledge base",
) -> RAGSystem:
    """
    Get or create a RAG system instance. Uses simple caching by index_name.

    Args:
        index_name: Pinecone index name (required, used as cache key)
        namespace: Pinecone namespace (required)
        description: Description of the knowledge base

    Returns:
        RAGSystem instance
    """
    if not index_name:
        # Try to get from environment variable
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            raise ValueError("index_name must be provided or PINECONE_INDEX_NAME environment variable must be set")
    
    if not namespace:
        raise ValueError("namespace must be provided")
    
    cache_key = f"{index_name}_{namespace}"
    if cache_key not in _rag_cache:
        _rag_cache[cache_key] = RAGSystem(
            index_name=index_name,
            namespace=namespace,
            description=description,
        )
    return _rag_cache[cache_key]
