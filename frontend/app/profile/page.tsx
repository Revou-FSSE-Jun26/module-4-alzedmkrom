import { redirect } from "next/navigation";
import { ProfileForm } from "@/components/ProfileForm";
import { getServerSession } from "@/lib/serverSession";
import { loginPath } from "@/lib/session";

// Protected page (FE-AUTH-05). Anonymous visitors are sent to login on the server.
export default async function ProfilePage() {
  const { user } = await getServerSession();
  if (user === null) {
    redirect(loginPath({ next: "/profile" }));
  }
  return <ProfileForm />;
}
