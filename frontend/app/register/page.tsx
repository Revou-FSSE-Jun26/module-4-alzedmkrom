import { redirect } from "next/navigation";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { getServerSession } from "@/lib/serverSession";

// A signed-in user is sent to the dashboard on the server (FE-AUTH-05).
export default async function RegisterPage() {
  const { user } = await getServerSession();
  if (user !== null) {
    redirect("/");
  }
  return <RegisterForm />;
}
