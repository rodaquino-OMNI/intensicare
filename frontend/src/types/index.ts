// Clinical dashboard type definitions

export interface PatientBedSummary {
  mpi_id: string;
  bed_id: string | null;
  display_name: string;
  unit: string | null;
  latest_mews: number | null;
  latest_news2: number | null;
  news2_risk: string | null; // low, medium, high
  mews_trend: string | null; // increasing, decreasing, stable
  news2_trend: string | null;
  active_alerts_count: number;
  highest_alert_severity: string | null; // info, warning, critical
  last_updated: string | null;
}

export interface DashboardResponse {
  patients: PatientBedSummary[];
  total: number;
  active_alerts_total: number;
}

export interface VitalsHistoryPoint {
  recorded_at: string;
  heart_rate: number | null;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  temperature: number | null;
  spo2: number | null;
  respiratory_rate: number | null;
  avpu: string | null;
  supplemental_o2: boolean | null;
}

export interface ScoreHistoryPoint {
  calculated_at: string;
  score_type: string;
  score_value: number;
  trend: string | null;
}

export interface AlertInfo {
  id: number;
  mpi_id: string;
  score_id: number | null;
  severity: string;
  status: string;
  title: string;
  body: string | null;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolution: string | null;
}

export interface PatientDetailResponse {
  mpi_id: string;
  bed_id: string | null;
  display_name: string;
  unit: string | null;
  vitals_history: VitalsHistoryPoint[];
  mews_history: ScoreHistoryPoint[];
  news2_history: ScoreHistoryPoint[];
  active_alerts: AlertInfo[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AlertListResponse {
  // Array of alerts with pagination info
  alerts: AlertInfo[];
  total?: number;
}
