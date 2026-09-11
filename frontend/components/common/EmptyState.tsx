import {ReactNode} from "react";

type EmptyStateProps = {
  children: ReactNode;
  className?: string;
};

export function EmptyState({
  children,
  className = "empty-panel"
}: EmptyStateProps) {
  return <div className={className}>{children}</div>;
}
