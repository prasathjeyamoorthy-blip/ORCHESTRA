# api/chain_instance.py
# Singleton holder for RAGChain — imported by both routes.py and voice.py
# to avoid circular imports.

from generation.chain import RAGChain

_chain: RAGChain | None = None

def get_chain() -> RAGChain:
    global _chain
    if _chain is None:
        _chain = RAGChain()
    return _chain
