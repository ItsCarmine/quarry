import { useEffect, useRef } from "react";
import { useTypst } from "../hooks/useTypst";

interface Props {
  typstSource: string;
  stage: string;
}

export function ReportViewer({ typstSource, stage }: Props) {
  const { svg, compiling, error, compile } = useTypst();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typstSource) {
      compile(typstSource);
    }
  }, [typstSource, compile]);

  if (!typstSource && !stage) {
    return (
      <div className="report-empty">
        <div className="report-empty-icon">&#x1F50D;</div>
        <h2>Quarry Research</h2>
        <p>Submit a research query to get started.</p>
      </div>
    );
  }

  if (stage && stage !== "done") {
    return (
      <div className="report-loading">
        <div className="spinner" />
        <p>
          {stage === "dispatching" && "Sending query to research backends..."}
          {stage === "synthesizing" && "Synthesizing findings..."}
          {stage === "generating" && "Generating report..."}
          {!["dispatching", "synthesizing", "generating"].includes(stage) &&
            `Working: ${stage}...`}
        </p>
      </div>
    );
  }

  return (
    <div className="report-viewer">
      {compiling && <div className="compile-badge">Compiling...</div>}
      {error ? (
        <div className="report-fallback">
          <div className="typst-error">Typst render unavailable: {error}</div>
          <pre className="typst-source">{typstSource}</pre>
        </div>
      ) : svg ? (
        <div
          ref={containerRef}
          className="report-svg"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : (
        <pre className="typst-source">{typstSource}</pre>
      )}
    </div>
  );
}
