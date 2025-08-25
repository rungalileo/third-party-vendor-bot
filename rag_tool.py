import os
from dotenv import load_dotenv
from langchain import hub
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

load_dotenv()


class RAGSystem:
    def __init__(
        self,
        index_name: str = None,
        namespace: str = None,
        model: str = "gpt-4.1",
        description: str = "Knowledge base",
    ):
        """
        Initialize a RAG (Retrieval-Augmented Generation) system.

        Args:
            index_name: Pinecone index name (required)
            namespace: Pinecone namespace (required)
            model: LLM model name (e.g., "gpt-4o-mini", "gpt-4")
            description: Description of the knowledge base
        """
        if not index_name:
            raise ValueError("index_name must be provided")
        if not namespace:
            raise ValueError("namespace must be provided")
        
        self.embeddings = None
        self.vectorstore = None
        self.retrieval_chain = None
        self.index = None
        self.index_name = index_name
        self.namespace = namespace
        self.model = model
        self.description = description
        self._initialized = False

    def initialize(self):
        """Initialize the RAG system to use existing Pinecone index"""
        if self._initialized:
            return

        try:
            # Initialize embeddings (must match the model used in setup script)
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large"
            )

            # Initialize Pinecone and connect to existing index
            pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
            
            # Check if index exists
            if not pc.has_index(self.index_name):
                raise ValueError(f"Pinecone index '{self.index_name}' does not exist. Please run scripts/setup_pinecone.py first.")
            
            # Connect to existing index
            self.index = pc.Index(self.index_name)
            print(f"[INDEX] Connected to existing index '{self.index_name}'")

            # Create vector store using existing index
            self.vectorstore = PineconeVectorStore(
                index=self.index, 
                embedding=self.embeddings, 
                namespace=self.namespace
            )

            # Set up retrieval chain
            self._setup_retrieval_chain()
            self._initialized = True

            print(f"✅ {self.description} RAG initialized successfully (using existing vectors)")

        except Exception as e:
            print(f"❌ Error initializing {self.description} RAG: {e}")
            import traceback
            traceback.print_exc()
            self._initialized = False



    def _setup_retrieval_chain(self):
        """Set up the retrieval chain for Q&A"""
        retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")

        # Configure retriever with namespace
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 4, "namespace": self.namespace}
        )

        # Create LLM
        llm = ChatOpenAI(
            temperature=0.0, 
            model=self.model, 
            name=f"Retriever-{self.description}"
        )

        combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
        self.retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)

    def search(self, query: str) -> str:
        """Search the configured knowledge base"""
        # Lazy initialization - only initialize when first used
        if not self._initialized:
            self.initialize()

        if not self.retrieval_chain:
            return f"{self.description} RAG system not initialized. Please check your environment variables and try again."

        try:
            result = self.retrieval_chain.invoke({"input": query})
            return result["answer"]
        except Exception as e:
            return f"Error during {self.description.lower()} RAG search: {str(e)}"


# Global cache for RAG instances
_rag_cache = {}


def get_rag_system(
    index_name: str = None,
    namespace: str = None,
    model: str = "gpt-4o-mini",
    description: str = "Knowledge base",
) -> RAGSystem:
    """
    Get or create a RAG system instance. Uses simple caching by index_name.

    Args:
        index_name: Pinecone index name (required, used as cache key)
        namespace: Pinecone namespace (required)
        model: LLM model name
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
            model=model,
            description=description,
        )
    return _rag_cache[cache_key]
