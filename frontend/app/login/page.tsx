import { redirect } from "next/navigation";
import { LoginForm } from "@/components/auth/LoginForm";
import { getServerSession } from "@/lib/serverSession";
import { safeNextPath } from "@/lib/session";

interface LoginPageProps {
  searchParams: Promise<{ next?: string | string[] }>;
}

// A signed-in user is sent away on the server, before any form is rendered (FE-AUTH-05).
export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { user } = await getServerSession();
  if (user !== null) {
    redirect("/");
  }
  const { next } = await searchParams;
  const rawNext = Array.isArray(next) ? next[0] : next;
  return <LoginForm next={safeNextPath(rawNext)} />;
}
