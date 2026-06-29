interface SubmitOverlayProps {
  title: string;
  message: string;
  steps: string[];
}

export function SubmitOverlay({ title, message, steps }: SubmitOverlayProps) {
  return (
    <div className="submit-overlay" role="dialog" aria-modal="true" aria-labelledby="submit-overlay-title">
      <div className="submit-overlay-card">
        <div className="submit-overlay-spinner" aria-hidden />
        <h3 id="submit-overlay-title">{title}</h3>
        <p>{message}</p>
        <ol className="submit-overlay-steps">
          {steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}
