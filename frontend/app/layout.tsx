import "./globals.css";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Toaster } from "react-hot-toast";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/context/AuthContext";
import { getServerSession } from "@/lib/serverSession";

export const metadata: Metadata = {
  title: "RevoTask",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

// A 401 from GET /api/users/me resolves to a null session inside getServerSession.
// Any other ApiError is not caught here, so it reaches app/global-error.tsx (Requirement 1.6).
export default async function RootLayout({ children }: { children: ReactNode }) {
  const { token, user } = await getServerSession();

  return (
    <html lang="en">
      <body>
        <AuthProvider initialToken={token} initialUser={user}>
          <AppShell>{children}</AppShell>
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  );
}
