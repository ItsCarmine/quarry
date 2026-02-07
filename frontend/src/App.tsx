import { useState, useCallback } from "react";
import { ChatSidebar } from "./components/ChatSidebar";
import { ReportViewer } from "./components/ReportViewer";
import { useWebSocket } from "./hooks/useWebSocket";
import type { ResearchResponse } from "./types";
import "./App.css";

function App() {
  const [reportId, setReportId] = useState<string | null>(null);
  const [researching, setResearching] = useState(false);

  const { stage, typstSource, error } = useWebSocket(reportId);

  // Reset researching state when pipeline finishes
  const isActive = researching && stage !== "done" && !error;

  const handleSubmit = useCallback(async (query: string) => {
    setResearching(true);

    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data: ResearchResponse = await res.json();
      setReportId(data.report_id);
    } catch {
      setResearching(false);
    }
  }, []);

  return (
    <div className="app">
      <main className="report-panel">
        <ReportViewer typstSource={typstSource} stage={isActive ? stage : typstSource ? "done" : ""} />
      </main>
      <ChatSidebar
        onSubmit={handleSubmit}
        stage={stage}
        error={error}
        disabled={isActive}
      />
    </div>
  );
}

export default App;
