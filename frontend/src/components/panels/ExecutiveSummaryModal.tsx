import { useEffect, useRef } from 'react';
import { useExecutiveSummary } from '../../hooks/useSimulations';
import { LoadingSpinner } from '../shared/LoadingSpinner';

const TIER_LABELS: Record<string, string> = {
  claude: 'Claude API',
  gemma: 'Gemma 4 2B',
  template: 'Template',
};

const SECTION_ORDER = [
  'executive_overview',
  'disruption_summary',
  'monte_carlo_results',
  'agent_recommendations',
  'roi_analysis',
  'risk_matrix',
] as const;

/** Simple markdown-to-HTML: tables, bold, line breaks */
function renderMarkdown(md: string): string {
  let html = md;

  // Tables
  const lines = html.split('\n');
  let inTable = false;
  const out: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      if (!inTable) {
        out.push('<table class="brief-table">');
        inTable = true;
      }
      // Skip separator rows
      if (/^\|[\s\-:|]+\|$/.test(trimmed)) {
        continue;
      }
      const cells = trimmed
        .split('|')
        .slice(1, -1)
        .map((c) => c.trim());
      const tag = !inTable || out[out.length - 1] === '<table class="brief-table">' ? 'th' : 'td';
      out.push('<tr>' + cells.map((c) => `<${tag}>${c}</${tag}>`).join('') + '</tr>');
    } else {
      if (inTable) {
        out.push('</table>');
        inTable = false;
      }
      out.push(line);
    }
  }
  if (inTable) out.push('</table>');
  html = out.join('\n');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Line breaks
  html = html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br/>');
  return `<p>${html}</p>`;
}

function ROIHighlight({ roi }: { roi: { mitigation_cost: number; avoided_loss: number; roi_pct: number; payback_days: number | null; revenue_at_risk_per_day: number } }) {
  const fmt = (v: number) => {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
    return `$${v.toFixed(0)}`;
  };

  if (roi.mitigation_cost === 0) return null;

  return (
    <div className="brief-roi-grid">
      <div className="brief-roi-card">
        <span className="brief-roi-label">Mitigation Cost</span>
        <span className="brief-roi-value" style={{ color: 'var(--wr-amber)' }}>{fmt(roi.mitigation_cost)}</span>
      </div>
      <div className="brief-roi-card">
        <span className="brief-roi-label">Avoided Loss</span>
        <span className="brief-roi-value" style={{ color: 'var(--wr-green)' }}>{fmt(roi.avoided_loss)}</span>
      </div>
      <div className="brief-roi-card brief-roi-card-highlight">
        <span className="brief-roi-label">Net ROI</span>
        <span className="brief-roi-value" style={{ color: roi.roi_pct > 0 ? 'var(--wr-green)' : 'var(--wr-red)' }}>
          {roi.roi_pct.toFixed(0)}%
        </span>
      </div>
      <div className="brief-roi-card">
        <span className="brief-roi-label">Payback Period</span>
        <span className="brief-roi-value" style={{ color: 'var(--wr-cyan)' }}>
          {roi.payback_days !== null ? `${roi.payback_days.toFixed(1)}d` : 'N/A'}
        </span>
      </div>
    </div>
  );
}

interface Props {
  simulationId: string;
  onClose: () => void;
}

export function ExecutiveSummaryModal({ simulationId, onClose }: Props) {
  const { data, isLoading, error } = useExecutiveSummary(simulationId);
  const contentRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="executive-brief-backdrop" onClick={onClose}>
      <div
        className="executive-brief-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="executive-brief-header no-print">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-bold" style={{ color: 'var(--wr-text-primary)' }}>
              Executive Brief
            </h2>
            {data && (
              <span className="executive-brief-tier-badge">
                {TIER_LABELS[data.llm_tier] || data.llm_tier}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button className="executive-brief-btn-print" onClick={handlePrint} disabled={!data}>
              Export PDF
            </button>
            <button className="executive-brief-btn-close" onClick={onClose}>
              &#x2715;
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="executive-brief-content" ref={contentRef}>
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <LoadingSpinner label="Generating executive brief..." />
              <span className="text-xs" style={{ color: 'var(--wr-text-muted)' }}>
                This may take a moment if using AI generation
              </span>
            </div>
          )}

          {error && (
            <div className="p-6 text-center">
              <p className="text-sm" style={{ color: 'var(--wr-red)' }}>
                Failed to generate executive summary
              </p>
              <p className="text-xs mt-2" style={{ color: 'var(--wr-text-muted)' }}>
                {(error as Error).message}
              </p>
            </div>
          )}

          {data && (
            <div className="executive-brief-print" id="executive-brief-print">
              {/* Print header (hidden on screen) */}
              <div className="print-only executive-brief-print-header">
                <h1>Supply Chain War Room — Executive Brief</h1>
                <p>{data.simulation_name} | Generated {new Date(data.generated_at).toLocaleDateString()}</p>
              </div>

              {/* ROI highlight card */}
              <ROIHighlight roi={data.raw_metrics.roi} />

              {/* Sections */}
              {SECTION_ORDER.map((key) => {
                const section = data.sections[key];
                if (!section) return null;
                // Skip ROI section from markdown if we rendered the highlight card
                if (key === 'roi_analysis' && data.raw_metrics.roi.mitigation_cost > 0) return null;
                return (
                  <div key={key} className="executive-brief-section">
                    <h3 className="executive-brief-section-title">{section.title}</h3>
                    <div
                      className="executive-brief-section-body"
                      dangerouslySetInnerHTML={{ __html: renderMarkdown(section.content) }}
                    />
                  </div>
                );
              })}

              {/* Footer */}
              <div className="executive-brief-footer">
                <span>Generated by Supply Chain War Room</span>
                <span>{new Date(data.generated_at).toLocaleString()} UTC</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
