// Decorative background behind every page (design: components/layout/PrismBackground.tsx).
// Purely visual: aria-hidden, no pointer events. The gradients live in app/globals.css.
export function PrismBackground() {
  return (
    <div className="prism-bg" aria-hidden="true">
      <span className="pb-ribbon pb-r1" />
      <span className="pb-ribbon pb-r2" />
    </div>
  );
}
