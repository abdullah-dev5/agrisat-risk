import type { RiskTier } from '../types';
import { RISK_COLORS, RISK_LABELS } from '../lib/constants';

export function RiskBadge({ tier }: { tier: RiskTier | null | undefined }) {
  const t = tier ?? 'normal';
  return (
    <span
      className="badge"
      style={{
        background: `${RISK_COLORS[t]}18`,
        color: RISK_COLORS[t],
        border: `1px solid ${RISK_COLORS[t]}33`,
      }}
    >
      <span className="badge-dot" />
      {RISK_LABELS[t]}
    </span>
  );
}
