"use client";

import { useRouter } from "next/navigation";
import { BaseButton } from "@/components/shared/BaseButton";

interface OpenBoardButtonProps {
  boardId: string;
}

// Secondary button that opens a board (Requirement 16.5). A Client Component because
// it needs an onClick handler; a Server Component cannot pass one.
export function OpenBoardButton({ boardId }: OpenBoardButtonProps) {
  const router = useRouter();

  return (
    <BaseButton variant="secondary" onClick={() => router.push("/boards/" + boardId)}>
      Open board
    </BaseButton>
  );
}
