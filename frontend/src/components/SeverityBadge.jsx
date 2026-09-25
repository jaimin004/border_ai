export default function SeverityBadge({ severity }) {
  return (
    <span className={`severity-badge ${severity || 'low'}`}>
      {severity || 'unknown'}
    </span>
  );
}
