import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskBadge } from './RiskBadge';

describe('RiskBadge', () => {
  it('renders the label for a known tier', () => {
    render(<RiskBadge tier="elevated" />);
    expect(screen.getByText('Elevated')).toBeInTheDocument();
  });

  it('renders the high-risk label distinctly from elevated', () => {
    render(<RiskBadge tier="high" />);
    expect(screen.getByText('High Risk')).toBeInTheDocument();
  });

  it('falls back to "Normal" when tier is null or undefined', () => {
    render(<RiskBadge tier={null} />);
    expect(screen.getByText('Normal')).toBeInTheDocument();
  });

  it('renders the "No Data" label for insufficient_data', () => {
    render(<RiskBadge tier="insufficient_data" />);
    expect(screen.getByText('No Data')).toBeInTheDocument();
  });
});
