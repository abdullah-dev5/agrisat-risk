export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="var(--forest)" />
      <path
        d="M10 28V18l10-6 10 6v10"
        stroke="var(--wheat)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="20" cy="14" r="2.5" fill="var(--wheat)" opacity="0.9" />
      <path d="M14 28h12" stroke="var(--cream)" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}
