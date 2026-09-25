import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#10b981',
};

const PIE_COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-default)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: '0.82rem',
    }}>
      <p style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || 'var(--accent-cyan)', marginTop: 2 }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
};

export function TimelineChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="period" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="count"
          name="Events"
          stroke="#22d3ee"
          strokeWidth={2}
          fill="url(#colorEvents)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function SeverityPieChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="severity"
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={3}
          strokeWidth={0}
          label={({ severity, count }) => `${severity}: ${count}`}
        >
          {data.map((entry, i) => (
            <Cell
              key={entry.severity}
              fill={SEVERITY_COLORS[entry.severity] || PIE_COLORS[i % PIE_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function CameraBarChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
        <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={120} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="event_count" name="Events" fill="#22d3ee" radius={[0, 4, 4, 0]} barSize={16} />
        <Bar dataKey="active_alerts" name="Active Alerts" fill="#ef4444" radius={[0, 4, 4, 0]} barSize={16} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RiskDistributionChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" name="Events" radius={[4, 4, 0, 0]} barSize={32}>
          {data.map((entry, i) => {
            const colors = ['#10b981', '#3b82f6', '#3b82f6', '#f59e0b', '#ef4444'];
            return <Cell key={i} fill={colors[i] || '#22d3ee'} />;
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function EventTypeChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis
          dataKey="event_type"
          tick={{ fontSize: 10 }}
          tickFormatter={(v) => v?.replace(/_/g, ' ')}
        />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          content={<CustomTooltip />}
          labelFormatter={(v) => v?.replace(/_/g, ' ')}
        />
        <Bar dataKey="count" name="Events" fill="#8b5cf6" radius={[4, 4, 0, 0]} barSize={32} />
      </BarChart>
    </ResponsiveContainer>
  );
}
