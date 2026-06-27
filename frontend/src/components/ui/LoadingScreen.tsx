import { LogoMark } from './LogoMark';

export function LoadingScreen({ label = 'Loading portfolio…' }: { label?: string }) {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <LogoMark size={48} />
      <p>{label}</p>
    </div>
  );
}
