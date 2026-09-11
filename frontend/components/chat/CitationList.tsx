import {Citation} from "@/lib/api";

type CitationListProps = {
  citations?: Citation[];
};

export function CitationList({citations}: CitationListProps) {
  if (!citations?.length) {
    return null;
  }

  return (
    <div className="citations">
      {citations.slice(0, 3).map((citation) => (
        <div className="citation" key={`${citation.chunk_id}-${citation.rank}`}>
          <div className="citation-top">
            <span>#{citation.rank}</span>
            <span>
              Doc {citation.document_id}
              {citation.page_number ? ` · Trang ${citation.page_number}` : ""}
            </span>
          </div>
          <div className="citation-title">{citation.document_title}</div>
          <div className="citation-snippet">{citation.snippet}</div>
        </div>
      ))}
    </div>
  );
}
