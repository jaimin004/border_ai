export default function RiskBreakdown({ breakdown = [], totalScore = 0, severity = 'low' }) {
  const maxPoints = 30; // max single factor weight

  const severityColor = {
    critical: 'var(--color-critical)',
    high: 'var(--color-high)',
    medium: 'var(--color-medium)',
    low: 'var(--color-low)',
  }[severity] || 'var(--accent-cyan)';

  const formatFactor = (name) =>
    name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div>
      <div className="risk-breakdown">
        {breakdown.map((item, i) => (
          <div className="risk-factor" key={i}>
            <div style={{ flex: 1 }}>
              <div className="risk-factor-name">{formatFactor(item.factor)}</div>
              <div
                className="risk-factor-bar"
                style={{
                  width: `${(item.points / maxPoints) * 100}%`,
                  background: severityColor,
                  marginTop: 4,
                }}
              />
            </div>
            <div className="risk-factor-points" style={{ color: severityColor }}>
              +{item.points}
            </div>
          </div>
        ))}
      </div>
      <div className="risk-total" style={{ borderColor: severityColor }}>
        <div className="risk-total-value" style={{ color: severityColor }}>
          {totalScore}
        </div>
        <div className="risk-total-label">Total Risk Score</div>
      </div>
    </div>
  );
}
