import {DocumentChunkItem} from "@/lib/api";
import {EmptyState} from "@/components/common/EmptyState";
import {LoadingLine} from "@/components/common/LoadingLine";

type ChunkListProps = {
  chunks: DocumentChunkItem[];
  loading: boolean;
};

export function ChunkList({chunks, loading}: ChunkListProps) {
  if (loading) {
    return <LoadingLine>Đang tải chunk...</LoadingLine>;
  }

  if (chunks.length === 0) {
    return <EmptyState>Tài liệu này chưa có chunk.</EmptyState>;
  }

  return (
    <>
      {chunks.slice(0, 80).map((chunk) => (
        <article className="chunk-item" key={chunk.id}>
          <header>
            <span>Chunk {chunk.chunk_index}</span>
            <span>
              {chunk.page_number ? `Trang ${chunk.page_number}` : "Không rõ trang"}
              {" · "}
              {chunk.token_count} tokens
              {" · "}
              {chunk.has_embedding ? "Có vector" : "Chưa có vector"}
            </span>
          </header>
          {chunk.section_title ? <strong>{chunk.section_title}</strong> : null}
          <p>{chunk.content}</p>
        </article>
      ))}
    </>
  );
}
