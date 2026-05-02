import React, { useState, useEffect } from 'react';
import { useRealtimeStats } from '../hooks/useRealtimeStats';
import { useDevices } from '../hooks/useDevices';
import StatsCard from './StatsCard';
import ZoneChart from './ZoneChart';
import DeviceList from './DeviceList';
import ConnectionStatus from './ConnectionStatus';
import ExportFilters from './ExportFilters';
import ThresholdSettings from './ThresholdSettings';
import TimeRangeSelector from './TimeRangeSelector';
import { Activity, Users, Wifi, WifiOff, RefreshCw, Settings, Eye, EyeOff } from 'lucide-react';

const Dashboard = () => {
  const [timeConfig, setTimeConfig] = useState({ mode: 'preset', value: 5 });
  const [selectedDeviceId, setSelectedDeviceId] = useState('');

  // Auto-refresh siempre activo en modo preset
  const { stats, loading, error, wsConnected, refresh } = useRealtimeStats(
    timeConfig,
    timeConfig.mode === 'preset', // Auto-refresh solo en modo preset
    selectedDeviceId
  );

  const { devices, loading: devicesLoading } = useDevices(false);
  const [showInactive, setShowInactive] = useState(true);  // mostrar todos por defecto en el apartado "Dispositivos IoT"

  // Filtrar solo dispositivos activos para el selector
  const activeDevices = devices.filter(d => d.is_active);
  const showDeviceSelector = activeDevices.length > 1; // Mostrar solo si hay más de uno

  // Auto-refresh cada 30 segundos en modo preset
  useEffect(() => {
    if (timeConfig.mode === 'custom') return;

    const interval = setInterval(() => {
      console.log('Recargando automáticamente las estadísticas...');
      refresh();
    }, 30000);

    return () => clearInterval(interval);
  }, [timeConfig.mode, refresh]);

  const handleTimeRangeChange = (newConfig) => {
    console.log('Rango de tiempo cambiado:', newConfig);
    setTimeConfig(newConfig);
  };

  // Función para obtener la descripción del filtro de tiempo
  const getTimeFilterLabel = () => {
    if (timeConfig.mode === 'custom' && timeConfig.startDateTime && timeConfig.endDateTime) {
      // Formatear fechas personalizadas
      const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleString('es-ES', {
          day: '2-digit',
          month: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        });
      };
      return `${formatDate(timeConfig.startDateTime)} - ${formatDate(timeConfig.endDateTime)}`;
    }

    // Para modo preset
    const minutes = timeConfig.value || 5;
    if (minutes === 1) return 'Último minuto';
    if (minutes === 5) return 'Últimos 5 minutos';
    if (minutes === 30) return 'Últimos 30 minutos';
    if (minutes === 60) return 'Última hora';
    if (minutes === 720) return 'Últimas 12 horas';
    if (minutes === 1440) return 'Último día';
    if (minutes === 10080) return 'Últimos 7 días';

    // Fallback para otros valores
    if (minutes < 60) {
      return `Últimos ${minutes} minutos`;
    } else if (minutes < 1440) {
      const hours = Math.floor(minutes / 60);
      return `Últimas ${hours} hora${hours !== 1 ? 's' : ''}`;
    } else {
      const days = Math.floor(minutes / 1440);
      return `Últimos ${days} día${days !== 1 ? 's' : ''}`;
    }
  };

  const getTimeWindowDescription = () => {
    if (timeConfig.mode === 'custom' && timeConfig.startDate && timeConfig.endDate) {
      return `Rango: ${timeConfig.startDate} - ${timeConfig.endDate}`;
    }
    const minutes = timeConfig.value || 5;
    if (minutes < 60) {
      return `Ventana de tiempo: ${minutes} minuto${minutes !== 1 ? 's' : ''}`;
    } else if (minutes < 1440) {
      const hours = Math.floor(minutes / 60);
      return `Ventana de tiempo: ${hours} hora${hours !== 1 ? 's' : ''}`;
    } else {
      const days = Math.floor(minutes / 1440);
      return `Ventana de tiempo: ${days} día${days !== 1 ? 's' : ''}`;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600">Cargando estadísticas...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <WifiOff className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <p className="text-red-600">Error al cargar datos: {error}</p>
          <button
            onClick={refresh}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const totalStats = stats?.total || {};
  const byZone = stats?.by_zone || {};

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900">
              Sistema de Detección Bluetooth
            </h1>
            <p className="text-sm md:text-base text-gray-600 mt-1">
              Monitoreo en tiempo real • {getTimeFilterLabel()}
            </p>
          </div>

        <div className="flex items-center gap-4 flex-wrap">
          <ConnectionStatus connected={wsConnected} />

          {showDeviceSelector && (
            <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Dispositivo:
                </label>
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm bg-white"
              >
                <option value="">Todos los dispositivos</option>
                {activeDevices.map((device) => (
                  <option key={device.device_id} value={device.device_id}>
                    {device.name || device.device_id}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-2 flex-1 justify-end">
            <TimeRangeSelector
              onTimeRangeChange={handleTimeRangeChange}
              currentValue={timeConfig.value}
            />

            <button
              onClick={refresh}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2 whitespace-nowrap"
            >
              <RefreshCw className="w-4 h-4" />
              Actualizar
            </button>
          </div>
        </div>
      </div>
    </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatsCard
          title="Dispositivos Detectados"
          value={totalStats.unique_devices || 0}
          icon={<Wifi className="w-6 h-6" />}
          color="blue"
          subtitle={`${totalStats.total_detections || 0} detecciones totales`}
        />

        <StatsCard
          title="Personas Estimadas"
          value={totalStats.estimated_people || 0}
          icon={<Users className="w-6 h-6" />}
          color="green"
          subtitle="Basado en ratio 1.5 dispositivos/persona"
        />

        <ThresholdSettings />

      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Distribución por Zonas</h2>
          <ZoneChart data={byZone} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Detalle por Zona</h2>
          <div className="space-y-4">
            {Object.entries(byZone).map(([zone, data]) => (
              <div key={zone} className="border-l-4 border-blue-500 pl-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold capitalize">{zone}</h3>
                    <p className="text-sm text-gray-600">
                      {data.unique_devices} dispositivos únicos
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-blue-600">
                      {data.estimated_people}
                    </p>
                    <p className="text-sm text-gray-600">personas</p>
                  </div>
                </div>
                {data.avg_rssi && (
                  <p className="text-xs text-gray-500 mt-1">
                    RSSI promedio: {data.avg_rssi.toFixed(1)} dBm
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              Dispositivos IoT ({showInactive ? devices.length : devices.filter(d => d.is_active).length})
            </h2>

            <button
              onClick={() => setShowInactive(!showInactive)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              {showInactive ? (
                <>
                  <EyeOff className="w-4 h-4" />
                  Ocultar inactivos
                </>
              ) : (
                <>
                  <Eye className="w-4 h-4" />
                  Mostrar todos
                </>
              )}
            </button>
          </div>

          <DeviceList
            devices={showInactive ? devices : devices.filter(d => d.is_active)}
            loading={devicesLoading}
          />
        </div>

        <div className="lg:col-span-1">
          <ExportFilters />
        </div>
      </div>

      <div className="mt-8 text-center text-sm text-gray-500">
        <p>
          Última actualización: {stats?.timestamp ? new Date(stats.timestamp).toLocaleTimeString('es-ES') : 'N/A'}
        </p>
        <p className="mt-1">
          {getTimeWindowDescription()}
        </p>
        {timeConfig.mode === 'preset' && (
          <p className="mt-1 text-green-600">
            ● Actualización automática (cada 30s)
          </p>
        )}
      </div>
    </div>
  );
};

export default Dashboard;