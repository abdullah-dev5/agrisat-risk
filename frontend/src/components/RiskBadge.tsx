import type { RiskTier } from '../types';
import { RISK_COLORS, RISK_LABELS } from '../lib/constants';

export function RiskBadge({ tier }: { tier: RiskTier | null | undefined }) {
  const t = tier ?? 'normal';
  return (
    <span className="badge" style={{ background: RISK_COLORS[t], color: '#0f172a' }}>
      {RISK_LABELS[t]}
    </span>
  );
}
