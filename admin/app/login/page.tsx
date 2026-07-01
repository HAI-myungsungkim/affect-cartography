"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await adminLogin(code);
      router.push("/users");
    } catch (err: any) {
      setError(err.message || "로그인 실패");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-10">
          <h1 className="text-2xl font-bold text-primary mb-2">
            Affect Cartography
          </h1>
          <p className="text-sm text-gray-500 mb-8">
            KAIST 정신건강 파일럿 연구 — 관리자 콘솔
          </p>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                관리자 코드
              </label>
              <input
                type="password"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl
                           focus:outline-none focus:ring-2 focus:ring-primary
                           text-base"
                placeholder="••••••••"
                autoFocus
              />
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200
                              rounded-lg p-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !code}
              className="w-full bg-primary text-white py-3 rounded-xl
                         font-semibold hover:bg-primary-dark transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "로그인 중..." : "로그인"}
            </button>
          </form>

          <p className="mt-8 text-xs text-gray-400 leading-relaxed">
            관리자 코드는 서버 .env 파일에서 설정합니다.
            <br />
            IP 화이트리스트 + 2FA는 운영 환경에서 추가 설정해야 합니다.
          </p>
        </div>
      </div>
    </div>
  );
}
