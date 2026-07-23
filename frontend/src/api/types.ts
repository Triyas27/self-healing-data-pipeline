export interface RunSummary {
  id: number;
  started_at: string;
  finished_at: string | null;
  row_count: number;
  clean_first_pass: number;
  healed: number;
  quarantined: number;
  error_types: Record<string, number>;
  fixes_applied: Record<string, number>;
  avg_time_to_heal_ms: number | null;
  status: string;
}

export interface DiagnosisHistoryEntry {
  hypothesis: string;
  transform: string | null;
  confidence: number;
  reasoning: string;
  source: string;
  row_after: Record<string, string> | null;
}

export interface QuarantineRow {
  id: number;
  run_id: number;
  original_data: Record<string, string>;
  error_type: string;
  error_detail: string;
  attempt_count: number;
  diagnosis_history: DiagnosisHistoryEntry[];
  resolved: boolean;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  run_id: number;
  row_identifier: string;
  hypothesis: string | null;
  transform_chosen: string | null;
  confidence: number | null;
  reasoning: string | null;
  diagnosis_source: string;
  outcome: string;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
}

export interface HealRatePoint {
  run_id: number;
  started_at: string;
  heal_rate: number;
}

export interface StatsOut {
  total_runs: number;
  total_rows_processed: number;
  total_clean_first_pass: number;
  total_healed: number;
  total_quarantined: number;
  overall_heal_rate: number;
  auto_heal_rate: number;
  heal_rate_over_time: HealRatePoint[];
  error_type_totals: Record<string, number>;
  fixes_applied_totals: Record<string, number>;
}

export const FAILURE_MODES = [
  "schema_drift",
  "type_mismatch",
  "date_format_swap",
  "encoding_issue",
  "null_required_field",
  "invalid_foreign_key",
] as const;

export type FailureMode = (typeof FAILURE_MODES)[number];

export interface TriggerRunParams {
  row_count: number;
  failure_rate: number;
  failure_mode?: FailureMode;
  seed?: number;
  use_llm?: boolean;
}
