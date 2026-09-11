import {ReactNode} from "react";

type LoadingLineProps = {
  children: ReactNode;
};

export function LoadingLine({children}: LoadingLineProps) {
  return <div className="loading-line">{children}</div>;
}
