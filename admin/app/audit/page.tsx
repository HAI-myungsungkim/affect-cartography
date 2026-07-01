"use client";

import { useEffect, useState } from "react";
import { api, DialogueAuditItem } from "@/lib/api";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

export default function AuditPage() {
  const [items, setItems] = useState<DialogueAuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  const load = async () => {
    setLoading(true);
    try {
      const list = await api.auditDialogues(20, days);
      setItems(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [days]);

  return (
    <AuthGuard>
      <Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">대화 감사</h1>
            <p className="text-sm text-gray-500 mt-1">
              최근 LLM 응답 표본을 검토하여 부적절한 응답을 식별. 사양서 5항.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value={1}>최근 1일</option>
              <option value={3}>최근 3일</option>
              <option value={7}>최근 7일</option>
              <option value={30}>최근 30일</option>
            </select>
            <button
              onClick={load}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
            >
              새로고침
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-gray-500">불러오는 중...</p>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-500">최근 대화 기록이 없습니다.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <AuditCard key={item.record_id} item={item} />
            ))}
          </div>
        )}
      </main>
    </AuthGuard>
  );
}

function AuditCard({ item }: { item: DialogueAuditItem }) {
  return (
    <div className={`bg-white rounded-xl border p-5 ${item.flagged ? "border-red-300" : "border-gray-200"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="font-semibold">{item.participant_code}</span>
          <span className="text-xs text-gray-500">
            {item.quadrant.toUpperCase()} V={item.valence.toFixed(2)} A={item.arousal.toFixed(2)}
          </span>
          {item.flagged && (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded font-semibold">
              ⚠ 안전 플래그
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.timestamp)}</span>
      </div>

      <div className="space-y-2 mt-3">
        {item.turns.map((t, i) => (
          <div
            key={i}
            className={`flex ${t.speaker === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                t.speaker === "user"
                  ? "bg-primary text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              <div className="text-xs opacity-70 mb-0.5">
                {t.speaker === "user" ? "사용자" : "에이전트"}
              </div>
              {t.message_text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR");
}
