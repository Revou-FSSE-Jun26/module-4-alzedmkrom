import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold text-gray-900">Page not found</h1>
      <Link href="/" className="text-blue-700 underline">
        Back to dashboard
      </Link>
    </main>
  );
}
