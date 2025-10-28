# Lazy imports to avoid circular dependencies
# Import submodules only when needed, not at package initialization

__all__ = [
    "BOQAgent",
    "get_agent",
    "OllamaClient",
    "get_ollama_client",
    "VectorStore",
    "get_vector_store",
    "RAGEngine",
    "get_rag_engine",
    "BOQTools"
]

def __getattr__(name):
    """Lazy load modules to avoid circular imports"""
    if name == "BOQAgent":
        from .agent import BOQAgent
        return BOQAgent
    elif name == "get_agent":
        from .agent import get_agent
        return get_agent
    elif name == "OllamaClient":
        from .ollama_client import OllamaClient
        return OllamaClient
    elif name == "get_ollama_client":
        from .ollama_client import get_ollama_client
        return get_ollama_client
    elif name == "VectorStore":
        from .vectorstore import VectorStore
        return VectorStore
    elif name == "get_vector_store":
        from .vectorstore import get_vector_store
        return get_vector_store
    elif name == "RAGEngine":
        from .rag_engine import RAGEngine
        return RAGEngine
    elif name == "get_rag_engine":
        from .rag_engine import get_rag_engine
        return get_rag_engine
    elif name == "BOQTools":
        from .tools import BOQTools
        return BOQTools
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
