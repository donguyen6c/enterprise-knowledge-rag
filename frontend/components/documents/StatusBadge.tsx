import {DocumentItem} from "@/lib/api";
import {statusLabel} from "@/lib/formatters";

type StatusBadgeProps = {
  status: DocumentItem["status"];
};

export function StatusBadge({status}: StatusBadgeProps) {
  return (
    <span className={`status-badge ${status.toLowerCase()}`}>
      {statusLabel(status)}
    </span>
  );
}
