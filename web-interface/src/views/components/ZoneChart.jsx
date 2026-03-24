import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getZoneLabel, getZoneColor } from '../../models/StatisticsModel';

function ZoneChart({ data, title = "Personas por cada zona" }) {
  if (!data || Object.keys(data).length === 0) {
    return <div style={{ padding: '40px', textAlign: 'center' }}>No hay datos disponibles</div>;
  }

  const chartData = Object.entries(data).map(([zone, value]) => ({
    zone: getZoneLabel(zone),
    people: value,
    fill: getZoneColor(zone)
  }));

  return (
    <div style={{
      background: '#fff', padding: '20px', borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '20px'
    }}>
      <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', fontWeight: '600' }}>{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="zone" />
          <YAxis label={{ value: 'Personas estimadas', angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(value) => [`${value} personas`, 'Estimación']} />
          <Legend />
          <Bar dataKey="people" name="Personas estimadas" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <p style={{ fontSize: '12px', color: '#9C9C9C', marginTop: '10px', fontStyle: 'italic' }}>
        * Estimación basada en dispositivos Bluetooth detectados
      </p>
    </div>
  );
}

export default ZoneChart;
