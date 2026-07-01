"use client";

import { useState } from "react";
import { api, getToken } from "@/lib/api";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

/**
 * 데이터 다운로드 페이지. 사양서 5항.
 *
 * - 구조화 측정 자료 CSV: 정동, 감정, 강도, 개입 응답
 * - 대화 로그 JSON: LLM과의 모든 턴
 * - 익명화 옵션 토글
 *
 * 인증된 fetch로 받은 후 브라우저에서 Blob 다운로드 — 단순 링크는 토큰 못 보내므로 X.
 */
export default function ExportPage() {
  const [anonymize, setAnonymize] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  const download = async (kind: "csv" | "dialogues") => {
    setDownloading(kind);
    try {
      const url = kind === "csv"
        ? api.downloadCsvUrl(anonymize)
        : api.downloadDialoguesUrl(anonymize);
      const token = getToken();
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`다운로드 실패: ${res.status}`);
      const blob = await res.blob();

      const ext = kind === "csv" ? "csv" : "json";
      const fname = `${kind === "csv" ? "affect_data" : "dialogues"}_${new Date().toISOString().slice(0, 10)}.${ext}`;
      const a = document.createElement("a");
      const blobUrl = URL.createObjectURL(blob);
      a.href = blobUrl;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <AuthGuard>
      <Nav />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="text-2xl font-bold mb-2">데이터 다운로드</h1>
        <p className="text-sm text-gray-500 mb-6">
          연구 종료 또는 중간 분석 시점에 다운로드합니다. 다운로드 로그는 서버에 기록됩니다.
        </p>

        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6 text-sm">
          <strong className="text-yellow-800">⚠ 익명화 옵션</strong>
          <p className="text-yellow-700 mt-1">
            기본값(ON)에서 실명이 자동으로 마스킹됩니다 (예: 김철수 → 김○○).
            IRB 사후 분석 시에는 ON으로 사용하고, 식별 정보가 필요한 보고에는 OFF를 사용하되
            데이터 취급에 각별히 유의해주세요.
          </p>
        </div>

        <div className="mb-6">
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={anonymize}
              onChange={(e) => setAnonymize(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="font-semibold">실명 익명화 (권장)</span>
          </label>
        </div>

        <div className="space-y-3">
          <DownloadCard
            title="구조화 측정 자료 (CSV)"
            description="정동 좌표, 감정 단어, 강도, 응답 시간, 분기 개입 응답을 통합한 CSV 파일."
            buttonLabel="CSV 다운로드"
            onClick={() => download("csv")}
            loading={downloading === "csv"}
          />

          <DownloadCard
            title="대화 로그 (JSON)"
            description="LLM 에이전트와의 모든 대화 턴 (record_id 단위로 그룹). 질적 분석용."
            buttonLabel="JSON 다운로드"
            onClick={() => download("dialogues")}
            loading={downloading === "dialogues"}
          />
        </div>

        <div className="mt-12 text-xs text-gray-500 leading-relaxed">
          <p><strong>데이터 보존 정책</strong>: 연구 종료 후 6개월 보관, 이후 익명화 분석셋만 유지.</p>
          <p className="mt-1">관리자 IP 화이트리스트 + 2FA는 운영 환경에서 반드시 활성화하세요.</p>
        </div>
      </main>
    </AuthGuard>
  );
}

function DownloadCard({
  title, description, buttonLabel, onClick, loading,
}: {
  title: string;
  description: string;
  buttonLabel: string;
  onClick: () => void;
  loading: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-start gap-4">
      <div className="flex-1">
        <h3 className="font-bold mb-1">{title}</h3>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
      <button
        onClick={onClick}
        disabled={loading}
        className="bg-primary text-white px-4 py-2 rounded-lg font-semibold
                   hover:bg-primary-dark disabled:opacity-50 whitespace-nowrap"
      >
        {loading ? "다운로드 중..." : buttonLabel}
      </button>
    </div>
  );
}
