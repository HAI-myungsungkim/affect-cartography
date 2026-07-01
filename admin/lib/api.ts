/**
 * 관리자 API 클라이언트.
 *
 * 기본 호스트는 환경 변수 NEXT_PUBLIC_API_BASE_URL에서 (default localhost:8000).
 * 토큰은 sessionStorage에 보관 — 브라우저 탭 닫으면 자동 만료.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "admin_token";
const DEVICE_KEY = "admin_device_id";

function getDeviceId(): string {
  if (typeof window === "undefined") return "server-side";
  let d = window.localStorage.getItem(DEVICE_KEY);
  if (!d) {
    d = "admin-" + Math.random().toString(36).slice(2, 10) +
      "-" + Date.now().toString(36);
    window.localStorage.setItem(DEVICE_KEY, d);
  }
  return d;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  window.sessionStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  window.sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401 || res.status === 403) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("관리자 인증 만료");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  // 파일 다운로드 응답은 별도 처리
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    return (await res.text()) as unknown as T;
  }

  return res.json();
}

// ===== Auth =====

export async function adminLogin(adminCode: string): Promise<{ access_token: string }> {
  const res = await fetch(`${API_BASE}/auth/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      admin_code: adminCode,
      device_id: getDeviceId(),
    }),
  });
  if (!res.ok) throw new Error("관리자 코드가 올바르지 않습니다");
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

// ===== Types =====

export interface AdminUser {
  user_id: string;
  participant_code: string;
  real_name: string;
  registered_at: string;
  first_login_at: string | null;
  last_response_at: string | null;
  total_records: number;
  response_rate: number;
  safety_flag_count: number;
  status: string;
  record_mode: string;
  has_device_bound: boolean;
}

export interface AdminUserDetail {
  user_id: string;
  participant_code: string;
  real_name: string;
  registered_at: string;
  status: string;
  record_mode: string;
  summary: {
    total_records: number;
    notification_responses: number;
    response_rate: number;
    days_active: number;
  };
  records: Array<{
    record_id: string;
    timestamp: string;
    valence: number;
    arousal: number;
    quadrant: string;
    mode: string;
    is_practice: boolean;
    trajectory_points: any[] | null;
    emotion_word: string | null;
    intensity: number | null;
    exploration_path: string[] | null;
    intervention_type: string | null;
    intervention_text: string | null;
    dialogue_turns: number;
  }>;
}

export interface SafetyFlag {
  flag_id: string;
  user_id: string;
  participant_code: string;
  real_name: string;
  flag_type: string;
  trigger_text: string | null;
  matched_keywords: string | null;
  raised_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface DialogueAuditItem {
  record_id: string;
  participant_code: string;
  quadrant: string;
  valence: number;
  arousal: number;
  timestamp: string;
  turns: Array<{
    turn_index: number;
    speaker: string;
    message_text: string;
    timestamp: string;
  }>;
  flagged: boolean;
}

// ===== Endpoints =====

export const api = {
  listUsers: (anonymize = false) =>
    request<{ total: number; users: AdminUser[] }>(`/admin/users?anonymize=${anonymize}`),

  getUserDetail: (userId: string, anonymize = false) =>
    request<AdminUserDetail>(`/admin/users/${userId}?anonymize=${anonymize}`),

  createParticipant: (participantCode: string, realName: string = "") =>
    request<AdminUser>(`/admin/users`, {
      method: "POST",
      body: JSON.stringify({ participant_code: participantCode, real_name: realName }),
    }),

  unbindDevice: (userId: string) =>
    request<{ message: string }>(`/admin/users/${userId}/unbind-device`, {
      method: "POST",
    }),

  listSafetyFlags: (unreviewedOnly = false) =>
    request<SafetyFlag[]>(`/admin/safety-flags?unreviewed_only=${unreviewedOnly}`),

  reviewFlag: (flagId: string, reviewedBy: string, note?: string) =>
    request<{ flag_id: string }>(`/admin/safety-flags/${flagId}/review`, {
      method: "POST",
      body: JSON.stringify({ reviewed_by: reviewedBy, note }),
    }),

  auditDialogues: (limit = 20, days = 7) =>
    request<DialogueAuditItem[]>(`/admin/dialogues/audit?limit=${limit}&days=${days}`),

  downloadCsvUrl: (anonymize = true) =>
    `${API_BASE}/admin/export/csv?anonymize=${anonymize}`,

  downloadDialoguesUrl: (anonymize = true) =>
    `${API_BASE}/admin/export/dialogues.json?anonymize=${anonymize}`,
};
