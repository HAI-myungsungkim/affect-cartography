"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, AdminUserDetail } from "@/lib/api";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;

  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getUserDetail(userId)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [userId]);

  const onUnbind = async () => {
    if (!confirm("정말 디바이스 바인딩을 해제하시겠습니까?\n사용자는 새 기기에서 로그인할 수 있게 됩니다.")) return;
    try {
      const r = await api.unbindDevice(userId);
      alert(r.message);
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <AuthGuard>
      <Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <button
          onClick={() => router.push("/users")}
          className="text-sm text-gray-500 hover:text-primary mb-4"
        >
          ← 사용자 목록
        </button>

        {loading ? (
          <p className="text-gray-500">불러오는 중...</p>
        ) : error ? (
          <p className="text-red-600">{error}</p>
        ) : detail ? (
          <>
            <div className="flex items-start justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold">
                  {detail.participant_code}{" "}
                  <span className="text-gray-400 font-normal">·</span>{" "}
                  <span className="text-gray-700">{detail.real_name || "—"}</span>
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  가입 {formatDate(detail.registered_at)} · 상태 {detail.status} · 모드 {detail.record_mode}
                </p>
              </div>
              <button
                onClick={onUnbind}
                className="px-4 py-2 border border-red-300 text-red-700 rounded-lg
                           hover:bg-red-50 text-sm font-semibold"
              >
                디바이스 바인딩 해제
              </button>
            </div>

            <div className="grid grid-cols-4 gap-4 mb-8">
              <Stat label="총 기록" value={detail.summary.total_records} />
              <Stat label="알림 응답" value={detail.summary.notification_responses} />
              <Stat
                label="응답률"
                value={`${Math.round(detail.summary.response_rate * 100)}%`}
              />
              <Stat label="활동일" value={detail.summary.days_active} />
            </div>

            <h2 className="text-lg font-bold mb-3">기록 ({detail.records.length})</h2>
            <div className="space-y-3">
              {detail.records.map((r) => (
                <RecordCard key={r.record_id} record={r} />
              ))}
              {detail.records.length === 0 && (
                <p className="text-gray-400 py-8 text-center">기록이 없습니다</p>
              )}
            </div>
          </>
        ) : null}
      </main>
    </AuthGuard>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-primary">{value}</div>
    </div>
  );
}

function RecordCard({ record }: { record: AdminUserDetail["records"][0] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <QuadrantPill q={record.quadrant} />
          <span className="text-xs text-gray-500">
            V={record.valence.toFixed(2)} A={record.arousal.toFixed(2)}
          </span>
          {record.mode === "trajectory" && (
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
              궤도 {record.trajectory_points?.length || 0}점
            </span>
          )}
          {record.is_practice && (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              연습
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">{formatDate(record.timestamp)}</span>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-xs text-gray-500 mb-1">감정 단어</div>
          {record.emotion_word ? (
            <div>
              <span className="font-semibold">{record.emotion_word}</span>
              <span className="text-gray-500 ml-2">강도 {record.intensity}</span>
              {record.exploration_path && record.exploration_path.length > 1 && (
                <div className="text-xs text-gray-400 mt-1">
                  경로: {record.exploration_path.join(" → ")}
                </div>
              )}
            </div>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </div>

        <div>
          <div className="text-xs text-gray-500 mb-1">개입</div>
          {record.intervention_type ? (
            <div>
              <InterventionPill type={record.intervention_type} />
              {record.intervention_text && (
                <div className="text-xs text-gray-600 mt-1 italic">
                  "{record.intervention_text}"
                </div>
              )}
            </div>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </div>

        <div>
          <div className="text-xs text-gray-500 mb-1">대화 턴</div>
          <span>{record.dialogue_turns}회</span>
        </div>
      </div>
    </div>
  );
}

function QuadrantPill({ q }: { q: string }) {
  const map: Record<string, { label: string; color: string }> = {
    q1: { label: "Q1 유쾌+고각성", color: "bg-orange-100 text-orange-700" },
    q2: { label: "Q2 불쾌+고각성", color: "bg-pink-100 text-pink-700" },
    q3: { label: "Q3 불쾌+저각성", color: "bg-blue-100 text-blue-700" },
    q4: { label: "Q4 유쾌+저각성", color: "bg-green-100 text-green-700" },
  };
  const m = map[q] || { label: q, color: "bg-gray-100 text-gray-600" };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${m.color}`}>
      {m.label}
    </span>
  );
}

function InterventionPill({ type }: { type: string }) {
  const map: Record<string, string> = {
    self_distancing: "자기거리두기",
    grounding: "그라운딩",
    activation: "행동활성화",
  };
  return (
    <span className="text-xs bg-accent-sage/30 text-primary px-2 py-0.5 rounded">
      {map[type] || type}
    </span>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}
