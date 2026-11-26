import Link from "next/link";

// Shown when the board is missing or private and the viewer is not a member (BE-AZ-03, FE-PAGE-03).
// The copy does not reveal which of the two it is.
export default function BoardNotFound() {
  return (
    <main className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold text-gray-900">Board not found</h1>
      <p className="text-base text-gray-600">
        This board does not exist, or you do not have access to it.
      </p>
      <Link href="/" className="text-base font-medium text-blue-700 underline">
        Back to dashboard
      </Link>
    </main>
  );
}
