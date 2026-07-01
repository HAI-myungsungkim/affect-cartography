"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const navItems = [
  { href: "/users", label: "사용자" },
  { href: "/safety", label: "안전 플래그" },
  { href: "/audit", label: "대화 감사" },
  { href: "/export", label: "데이터 다운로드" },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  const onLogout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/users" className="text-lg font-bold text-primary">
            Affect Cartography <span className="font-normal text-gray-500">관리자</span>
          </Link>
          <div className="flex gap-6 text-sm">
            {navItems.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`hover:text-primary transition-colors ${
                    active ? "text-primary font-semibold" : "text-gray-600"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
        <button
          onClick={onLogout}
          className="text-sm text-gray-500 hover:text-red-600"
        >
          로그아웃
        </button>
      </div>
    </nav>
  );
}
