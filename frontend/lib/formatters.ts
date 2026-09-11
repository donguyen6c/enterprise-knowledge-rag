import {DocumentItem} from "@/lib/api";

export function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(new Date(value));
}

export function formatFileSize(value: number | null) {
  if (!value) {
    return "0 KB";
  }

  if (value < 1024 * 1024) {
    return `${Math.ceil(value / 1024)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function statusLabel(status: DocumentItem["status"]) {
  const labels: Record<DocumentItem["status"], string> = {
    UPLOADED: "Đang chờ",
    PROCESSING: "Đang xử lý",
    READY: "Sẵn sàng",
    FAILED: "Lỗi",
    ARCHIVED: "Đã lưu trữ"
  };

  return labels[status];
}
