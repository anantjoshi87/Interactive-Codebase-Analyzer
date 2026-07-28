from .models import CodeUnit, UnitType


class FallbackChunker:
    @staticmethod
    def parse(
        file_path: str,
        text_content: str,
        chunk_size: int = 100,
        overlap: int = 20,
    ) -> list[CodeUnit]:
        lines = text_content.splitlines()

        chunks = []

        if not lines:
            return chunks

        for i in range(0, len(lines), chunk_size - overlap):

            chunk_lines = lines[i : i + chunk_size]

            chunks.append(
                CodeUnit(
                    file_path=file_path,
                    unit_type=UnitType.CODE,
                    symbol_name=None,
                    symbol_kind="text_chunk",
                    ast_node_type="text_chunk",
                    start_line=i + 1,
                    end_line=i + len(chunk_lines),
                    start_byte=0,
                    end_byte=0,
                    code_content="\n".join(chunk_lines),
                    is_ast_parsed=False,
                )
            )

        return chunks
