"use client";

import { useEffect, useState } from "react";
import { api, SafetyFlag } from "@/lib/api";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

export default function SafetyPage() {
  const [flags, setFlags] = useState<SafetyFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreviewedOnly, setUnreviewedOnly] = useState(false);
  const [reviewer, setReviewer] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const list = await api.listSafetyFlags(unreviewedOnly);
      setFlags(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [unreviewedOnly]);

  const onReview = async (flagId: string) => {
    if (!reviewer.trim()) {
      alert("검토자 이름을 먼저 입력해주세요");
      return;
    }
    if (!confirm("이 플래그를 검토 완료로 표시하시겠습니까?")) return;
    try {
      await api.reviewFlag(flagId, reviewer.trim());
      await load();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <AuthGuard>
      <Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">안전 플래그</h1>
            <p className="text-sm text-gray-500 mt-1">
              위기 키워드 감지 시 자동 발급. 사양서 10항.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="검토자 이름"
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            />
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={unreviewedOnly}
                onChange={(e) => setUnreviewedOnly(e.target.checked)}
              />
              미검토만
            </label>
          </div>
        </div>

        {loading ? (
          <p className="text-gray-500">불러오는 중...</p>
        ) : flags.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-500">
              {unreviewedOnly ? "미검토 플래그가 없습니다." : "안전 플래그가 없습니다."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {flags.map((f) => (
              <FlagCard key={f.flag_id} flag={f} onReview={() => onReview(f.flag_id)} />
            ))}
          </div>
        )}
      </main>
    </AuthGuard>
  );
}

function FlagCard({ flag, onReview }: { flag: SafetyFlag; onReview: () => void }) {
  const typeMap: Record<string, { label: string; color: string }> = {
    suicide_ideation: { label: "자살 사고", color: "bg-red-100 text-red-800 border-red-300" },
    self_harm: { label: "자해", color: "bg-orange-100 text-orange-800 border-orange-300" },
    severe_distress: { label: "심한 절망", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
    other: { label: "기타", color: "bg-gray-100 text-gray-800 border-gray-300" },
  };
  const t = typeMap[flag.flag_type] || { label: flag.flag_type, color: "bg-gray-100 text-gray-800" };

  return (
    <div className={`bg-white rounded-xl border-2 p-5 ${flag.reviewed_at ? "border-gray-200" : t.color.split(" ")[2]}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold px-2 py-1 rounded ${t.color}`}>
            {t.label}
          </span>
          <span className="text-sm font-semibold">
            {flag.participant_code} · {flag.real_name}
          </span>
          {flag.reviewed_at && (
            <span className="text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded">
              ✓ 검토 완료 ({flag.reviewed_by})
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">{formatDate(flag.raised_at)}</span>
      </div>

      {flag.trigger_text && (
        <div className="bg-gray-50 rounded-lg p-3 mb-3 border-l-4 border-gray-300">
          <div className="text-xs text-gray-500 mb-1">트리거 텍스트:</div>
          <div className="text-sm text-gray-800">{flag.trigger_text}</div>
        </div>
      )}

      {flag.matched_keywords && (
        <div className="text-xs text-gray-500">
          매칭 키워드: <span className="font-mono">{flag.matched_keywords}</span>
        </div>
      )}

      {!flag.reviewed_at && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <button
            onClick={onReview}
            className="text-sm bg-primary text-white px-4 py-1.5 rounded-lg
                       hover:bg-primary-dark"
          >
            검토 완료로 표시
          </button>
        </div>
      )}
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR");
}
