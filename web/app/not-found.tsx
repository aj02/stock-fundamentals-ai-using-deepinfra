import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-3 text-[color:var(--color-muted-foreground)]">
        That URL didn&rsquo;t match anything.
      </p>
      <div className="mt-6">
        <Link href="/" className="text-sm underline-offset-2 hover:underline">
          ← Back to search
        </Link>
      </div>
    </div>
  );
}
