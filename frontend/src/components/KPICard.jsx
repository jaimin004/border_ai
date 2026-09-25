export default function KPICard({ icon: Icon, value, label, accent = 'cyan' }) {
  return (
    <div className={`kpi-card ${accent}`}>
      <div className="kpi-icon">
        <Icon size={22} />
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
