import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const ZoneChart = ({ data }) => {
  const chartData = Object.entries(data || {}).map(([zone, stats]) => ({
    name: zone.charAt(0).toUpperCase() + zone.slice(1),
    value: stats.estimated_people,
    devices: stats.unique_devices
  }));

  const COLORS = {
    'Near': '#FF474C',
    'Medium': '#FFA800',
    'Far': '#009CDD'
  };

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No hay datos disponibles
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#824eb6"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#824eb6'} />
          ))}
        </Pie>
        <Tooltip 
          formatter={(value, name, props) => [
            `${value} personas (${props.payload.devices} dispositivos)`,
            props.payload.name
          ]}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default ZoneChart;
