import { useEffect, useMemo, useState } from 'react';
import { GLOSSARY, GUIDE_SECTIONS, type GuideBlock } from '../content/guideContent';
import { PILOT_CROP, PILOT_DISTRICT, RISK_LABELS } from '../lib/constants';

type AudienceMode = 'all' | 'plain' | 'technical';

function showPlain(mode: AudienceMode) {
  return mode === 'all' || mode === 'plain';
}

function showTechnical(mode: AudienceMode) {
  return mode === 'all' || mode === 'technical';
}

function GuideBlockView({ block, mode }: { block: GuideBlock; mode: AudienceMode }) {
  return (
    <div className="guide-block">
      {block.heading && <h4 className="guide-block-heading">{block.heading}</h4>}
      {block.plain && showPlain(mode) && (
        <p className="guide-plain">{block.plain}</p>
      )}
      {block.technical && showTechnical(mode) && (
        <div className="guide-tech">
          <span className="guide-tech-label">Technical</span>
          <p>{block.technical}</p>
        </div>
      )}
      {block.bullets && block.bullets.length > 0 && (
        <ul className="guide-bullet-list">
          {block.bullets.map((item) => (
            <li key={item.label} className="guide-bullet-item">
              <strong>{item.label}</strong>
              {item.plain && showPlain(mode) && <p className="guide-plain">{item.plain}</p>}
              {item.technical && showTechnical(mode) && (
                <p className="guide-tech-inline">{item.technical}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function GuidePage() {
  const [mode, setMode] = useState<AudienceMode>('all');
  const [activeId, setActiveId] = useState(GUIDE_SECTIONS[0]?.id ?? 'overview');
  const [query, setQuery] = useState('');

  const filteredGlossary = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return GLOSSARY;
    return GLOSSARY.filter(
      (g) =>
        g.term.toLowerCase().includes(q) ||
        g.plain.toLowerCase().includes(q) ||
        g.technical.toLowerCase().includes(q),
    );
  }, [query]);

  useEffect(() => {
    const sections = document.querySelectorAll('.guide-section[id]');
    if (!sections.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target.id) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: '-20% 0px -55% 0px', threshold: [0, 0.25, 0.5] },
    );

    sections.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  function scrollTo(id: string) {
    setActiveId(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className="guide-page">
      <div className="page-header guide-page-header">
        <div>
          <span className="eyebrow">Documentation & guidance</span>
          <h1>How AgriSat Risk works</h1>
          <p className="page-intro">
            Plain-language tutorials and technical reference for {PILOT_CROP} monitoring in{' '}
            {PILOT_DISTRICT}. Use this page to understand baselines, vegetation readings, and risk flags.
          </p>
        </div>
        <div className="guide-mode-toggle" role="group" aria-label="Content audience">
          {(['all', 'plain', 'technical'] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={mode === value ? 'active' : ''}
              onClick={() => setMode(value)}
            >
              {value === 'all' ? 'Both' : value === 'plain' ? 'Plain language' : 'Technical'}
            </button>
          ))}
        </div>
      </div>

      <div className="guide-callout card">
        <strong>Start here if you are new:</strong> read{' '}
        <button type="button" className="guide-inline-link" onClick={() => scrollTo('overview')}>
          What AgriSat Risk does
        </button>
        , then{' '}
        <button type="button" className="guide-inline-link" onClick={() => scrollTo('baseline')}>
          Historical baseline
        </button>{' '}
        and{' '}
        <button type="button" className="guide-inline-link" onClick={() => scrollTo('risk-scoring')}>
          Risk scoring
        </button>
        . Loan officers can stay in plain language; engineers and agronomists can switch to Technical.
      </div>

      <div className="guide-layout">
        <aside className="guide-sidebar card" aria-label="Guide contents">
          <p className="section-title">On this page</p>
          <nav className="guide-nav">
            {GUIDE_SECTIONS.map((section) => (
              <button
                key={section.id}
                type="button"
                className={activeId === section.id ? 'active' : ''}
                onClick={() => scrollTo(section.id)}
              >
                {section.title}
              </button>
            ))}
            <button
              type="button"
              className={activeId === 'glossary' ? 'active' : ''}
              onClick={() => scrollTo('glossary')}
            >
              Glossary
            </button>
          </nav>

          <div className="guide-risk-legend">
            <p className="section-title">Risk tiers</p>
            <ul>
              {Object.entries(RISK_LABELS).map(([key, label]) => (
                <li key={key}>
                  <span className={`risk-dot risk-dot-${key}`} aria-hidden />
                  {label}
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <div className="guide-main">
          {GUIDE_SECTIONS.map((section) => (
            <article key={section.id} id={section.id} className="guide-section card card-elevated">
              <header className="guide-section-header">
                <h2>{section.title}</h2>
                <p className="guide-section-summary">{section.summary}</p>
              </header>
              {section.blocks.map((block, idx) => (
                <GuideBlockView key={`${section.id}-${idx}`} block={block} mode={mode} />
              ))}
            </article>
          ))}

          <article id="glossary" className="guide-section card card-elevated">
            <header className="guide-section-header">
              <h2>Glossary</h2>
              <p className="guide-section-summary">
                Search technical terms used across the platform and field reports.
              </p>
            </header>
            <label className="guide-search">
              <span className="sr-only">Search glossary</span>
              <input
                type="search"
                placeholder="Search terms (NDVI, baseline, z-score…)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <dl className="guide-glossary">
              {filteredGlossary.map((entry) => (
                <div key={entry.term} className="guide-glossary-entry">
                  <dt>{entry.term}</dt>
                  {showPlain(mode) && <dd className="guide-plain">{entry.plain}</dd>}
                  {showTechnical(mode) && (
                    <dd className="guide-tech-inline">{entry.technical}</dd>
                  )}
                </div>
              ))}
            </dl>
            {filteredGlossary.length === 0 && (
              <p className="guide-empty">No glossary entries match your search.</p>
            )}
          </article>

          <footer className="guide-footer card">
            <p className="section-title">Disclaimer</p>
            <p>
              AgriSat Risk provides satellite-derived decision-support for agricultural lenders and
              insurers. It does not constitute agronomic advice, credit approval, or insurance
              adjudication. Always validate flagged fields with ground truth when decisions matter.
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
}
