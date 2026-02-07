export interface ResearchResponse {
  brief_id: string;
  report_id: string;
}

export interface Citation {
  id: string;
  claim: string;
  llm_source: string;
  underlying_url: string | null;
  confidence: number;
}

export interface ReportResponse {
  report_id: string;
  brief_id: string;
  typst_source: string;
  citations: Citation[];
}

export type WSMessage =
  | { type: "status"; stage: string }
  | { type: "report"; typst_source: string }
  | { type: "error"; detail: string }
  | { type: "ack"; data: string };
