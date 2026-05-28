from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChunkingService:
    def split(self, text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> list[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n# ", "\n\n", "\n", ". ", " ", ""],
        )
        return [c.strip() for c in splitter.split_text(text) if c.strip()]

chunking_service = ChunkingService()
