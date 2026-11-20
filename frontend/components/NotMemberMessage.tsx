import Link from 'next/link';

export function NotMemberMessage() {
  return (
    <div>
      <p>You are not a member of this board</p>
      <Link href="/">Back to home</Link>
    </div>
  );
}
