import { redirect } from "next/navigation";

export default function Root() {
  // 항상 /login으로 시작 (AuthGuard가 토큰 있으면 /users로 보냄)
  redirect("/users");
}
