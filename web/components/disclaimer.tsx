/**
 * The disclaimer wording is mandatory across the project (README header,
 * UI footer, every API response, every report banner). Defining it once
 * here keeps wording consistent if anything changes.
 */

export const DISCLAIMER_TEXT =
  'Educational and engineering demo. NOT investment advice. NOT a recommendation to buy or sell any security.';

export function DisclaimerBanner({ subtle = false }: { subtle?: boolean }) {
  if (subtle) {
    return (
      <p className="text-xs text-[color:var(--color-muted-foreground)]">
        <span className="font-medium">Disclaimer:</span> {DISCLAIMER_TEXT}
      </p>
    );
  }
  return (
    <div className="border-y border-[color:var(--color-border)] bg-[color:var(--color-muted)]">
      <div className="mx-auto max-w-7xl px-4 py-2 text-center text-xs text-[color:var(--color-muted-foreground)]">
        <span className="font-medium">Disclaimer:</span> {DISCLAIMER_TEXT}{' '}
        Output is a structured summary of publicly available information for analytical study.
      </div>
    </div>
  );
}
