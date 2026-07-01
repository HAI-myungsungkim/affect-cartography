"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, AdminUser } from "@/lib/api";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [anonymize, setAnonymize] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const d = await api.listUsers(anonymize);
      setUsers(d.users);
      setLoading(false);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [anonymize]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.createParticipant(newCode.trim(), newName.trim());
      setShowCreate(false);
      setNewCode("");
      setNewName("");
      await load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <AuthGuard>
      <Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">사용자</h1>
            <p className="text-sm text-gray-500 mt-1">
              총 {users.length}명 · 피험자 코드 발급 / 디바이스 관리
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={anonymize}
                onChange={(e) => setAnonymize(e.target.checked)}
              />
              실명 익명화
            </label>
            <button
              onClick={() => setShowCreate(true)}
              className="bg-primary text-white px-4 py-2 rounded-lg text-sm
                         font-semibold hover:bg-primary-dark"
            >
              + 새 피험자 코드
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-gray-500">불러오는 중...</p>
        ) : error ? (
          <p className="text-red-600">{error}</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <Th>코드</Th>
                  <Th>실명</Th>
                  <Th>가입일</Th>
                  <Th>마지막 응답</Th>
                  <Th>응답률</Th>
                  <Th>기록 수</Th>
                  <Th>플래그</Th>
                  <Th>상태</Th>
                  <Th>기기</Th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <Td>
                      <Link
                        href={`/users/${u.user_id}`}
                        className="text-primary font-semibold hover:underline"
                      >
                        {u.participant_code}
                      </Link>
                    </Td>
                    <Td>{u.real_name || <span className="text-gray-400">—</span>}</Td>
                    <Td className="text-gray-500">{formatDate(u.registered_at)}</Td>
                    <Td className="text-gray-500">
                      {u.last_response_at ? formatDate(u.last_response_at) : <span className="text-gray-400">없음</span>}
                    </Td>
                    <Td>
                      <ResponseRateBadge rate={u.response_rate} />
                    </Td>
                    <Td>{u.total_records}</Td>
                    <Td>
                      {u.safety_flag_count > 0 ? (
                        <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-semibold">
                          {u.safety_flag_count}
                        </span>
                      ) : (
                        <span className="text-gray-300">0</span>
                      )}
                    </Td>
                    <Td>
                      <StatusBadge status={u.status} />
                    </Td>
                    <Td>
                      {u.has_device_bound ? (
                        <span className="text-green-600 text-xs">바인딩됨</span>
                      ) : (
                        <span className="text-gray-400 text-xs">없음</span>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 && (
              <p className="text-center py-12 text-gray-400">사용자가 없습니다</p>
            )}
          </div>
        )}

        {showCreate && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 w-full max-w-md">
              <h2 className="text-lg font-bold mb-4">새 피험자 코드 발급</h2>
              <form onSubmit={onCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    피험자 코드
                  </label>
                  <input
                    type="text"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    placeholder="P099"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-primary"
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    실명 (선택)
                  </label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="첫 로그인 시 사용자가 입력하므로 비워둬도 됩니다"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreate(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg
                               hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={creating || !newCode.trim()}
                    className="flex-1 bg-primary text-white px-4 py-2 rounded-lg
                               font-semibold disabled:opacity-50"
                  >
                    {creating ? "발급 중..." : "발급"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </AuthGuard>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
      {children}
    </th>
  );
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 ${className}`}>{children}</td>;
}

function ResponseRateBadge({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const color =
    rate >= 0.7 ? "text-green-700 bg-green-50" :
    rate >= 0.4 ? "text-yellow-700 bg-yellow-50" :
    "text-red-700 bg-red-50";
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${color}`}>
      {pct}%
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = { active: "활성", dropped: "이탈", completed: "완료" }[status] || status;
  const color = {
    active: "text-green-700 bg-green-50",
    dropped: "text-gray-600 bg-gray-100",
    completed: "text-blue-700 bg-blue-50",
  }[status] || "text-gray-600 bg-gray-100";
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${color}`}>
      {label}
    </span>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = (d.getMonth() + 1).toString().padStart(2, "0");
  const day = d.getDate().toString().padStart(2, "0");
  const hh = d.getHours().toString().padStart(2, "0");
  const mi = d.getMinutes().toString().padStart(2, "0");
  return `${y}-${m}-${day} ${hh}:${mi}`;
}
