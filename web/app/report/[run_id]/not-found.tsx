import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-24 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">Run not found</h1>
      <p className="mt-3 text-[color:var(--color-muted-foreground)]">
        Either this run never existed, or it&rsquo;s still in progress and hasn&rsquo;t persisted yet.
      </p>
      <div className="mt-6">
        <Link href="/" className="text-sm underline-offset-2 hover:underline">
          Start a new analysis →
        </Link>
      </div>
    </div>
  );
}
