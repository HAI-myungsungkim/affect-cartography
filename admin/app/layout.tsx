import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Affect Cartography 관리자",
  description: "KAIST 정신건강 파일럿 연구 관리 대시보드",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
