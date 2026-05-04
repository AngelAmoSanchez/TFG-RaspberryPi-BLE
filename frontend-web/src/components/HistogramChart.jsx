import React, { useState, useMemo } from 'react';
import {  BarChart,  Bar,  XAxis,  YAxis,  CartesianGrid,  Tooltip,  Legend,  ResponsiveContainer} from 'recharts';
import { BarChart3 } from 'lucide-react';
import { useHistogramStats } from '../hooks/useHistogramStats';

const COLORS = {
  near: '#FF474C',
  medium: '#FFA800',
  far: '#009CDD',
};

const RANGE_OPTIONS = [
  { value: 'hour', label: 'Última hora (cada 10 min)' },
  { value: 'today', label: 'Hoy (cada 3 horas)' },
  { value: 'week', label: 'Última semana (por día)' },
];

// Formatea la etiqueta del eje X según el rango.
const formatLabel = (bucket, range) => {
  const start = new Date(bucket.period_start);
  if (range === 'hour') {
    // 10:00, 10:10, 10:20...
    const hh = String(start.getHours()).padStart(2, '0');
    const mm = String(start.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }
  if (range === 'today') {
    // 00, 03, 06... (rangos de 3h)
    const hh = String(start.getHours()).padStart(2, '0');
    return `${hh}:00`;
  }
  if (range === 'week') {
    // lun 12, mar 13... (día abreviado + número)
    return start.toLocaleDateString('es-ES', {
      weekday: 'short',
      day: '2-digit',
    });
  }
  return '';
};

// Tooltip personalizado: muestra desglose por zona y el periodo concreto.
const CustomTooltip = ({ active, payload, label, range }) => {
  if (!active || !payload || !payload.length) return null;

  const datum = payload[0]?.payload;
  if (!datum) return null;

  const formatRange = () => {
    if (!datum.period_start || !datum.period_end) return label;
    const start = new Date(datum.period_start);
    const end = new Date(datum.period_end);
    if (range === 'week') {
      return start.toLocaleDateString('es-ES', {
        weekday: 'long',
        day: '2-digit',
        month: 'short',
      });
    }
    const fmt = (d) =>
      d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    return `${fmt(start)} - ${fmt(end)}`;
  };

  const total = (datum.near || 0) + (datum.medium || 0) + (datum.far || 0);

  return (
    <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200 text-sm">
      <p className="font-semibold text-gray-900 mb-2">{formatRange()}</p>
      <div className="space-y-1">
        <p className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-sm"
            style={{ backgroundColor: COLORS.near }}
          />
          <span className="text-gray-700">Near:</span>
          <span className="font-medium text-gray-900">{datum.near || 0}</span>
        </p>
        <p className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-sm"
            style={{ backgroundColor: COLORS.medium }}
          />
          <span className="text-gray-700">Medium:</span>
          <span className="font-medium text-gray-900">{datum.medium || 0}</span>
        </p>
        <p className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-sm"
            style={{ backgroundColor: COLORS.far }}
          />
          <span className="text-gray-700">Far:</span>
          <span className="font-medium text-gray-900">{datum.far || 0}</span>
        </p>
        <p className="pt-1 mt-1 border-t border-gray-100 text-gray-700">
          Total: <span className="font-semibold text-gray-900">{total}</span> dispositivos
        </p>
      </div>
    </div>
  );
};

const HistogramChart = ({ deviceId = '' }) => {
  const [range, setRange] = useState('hour'); // por defecto la última hora
  const { data, loading, error } = useHistogramStats(range, true, deviceId);

  // Transforma la respuesta del backend a los valores que espera Recharts.
  const chartData = useMemo(() => {
    if (!data?.buckets) return [];
    return data.buckets.map((bucket) => ({
      label: formatLabel(bucket, range),
      period_start: bucket.period_start,
      period_end: bucket.period_end,
      near: bucket.by_zone?.near || 0,
      medium: bucket.by_zone?.medium || 0,
      far: bucket.by_zone?.far || 0,
    }));
  }, [data, range]);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          Evolución temporal
        </h2>
        <select
          value={range}
          onChange={(e) => setRange(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {RANGE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center h-64 text-gray-400">
          Cargando histograma...
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-64 text-red-400 text-sm">
          Error: {error}
        </div>
      ) : chartData.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-gray-400">
          No hay datos disponibles
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: '#6b7280' }}
              interval={0}
            />
            <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} allowDecimals={false} />
            <Tooltip content={<CustomTooltip range={range} />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
              formatter={(value) => {
                const map = { near: 'Near', medium: 'Medium', far: 'Far' };
                return map[value] || value;
              }}
            />
            <Bar dataKey="near" stackId="zones" fill={COLORS.near} />
            <Bar dataKey="medium" stackId="zones" fill={COLORS.medium} />
            <Bar dataKey="far" stackId="zones" fill={COLORS.far} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default HistogramChart;
