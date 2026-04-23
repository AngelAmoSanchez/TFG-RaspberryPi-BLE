import React, { useState } from 'react';
import { useRealtimeStats } from '../hooks/useRealtimeStats';
import { useDevices } from '../hooks/useDevices';
import StatsCard from './StatsCard';
import ZoneChart from './ZoneChart';
import DeviceList from './DeviceList';
import ConnectionStatus from './ConnectionStatus';
import ExportFilters from './ExportFilters';
import TimeRangeSelector from './TimeRangeSelector';
import { Activity, Users, Wifi, WifiOff } from 'lucide-react';

const Dashboard = () => {
  const [timeConfig, setTimeConfig] = useState({ mode: 'preset', value: 5 });
  const { stats, loading, error, wsConnected, refresh } = useRealtimeStats(timeConfig);
  const { devices, loading: devicesLoading } = useDevices(true);

  const handleTimeRangeChange = (newConfig) => {
    console.log('Time range changed:', newConfig);
    setTimeConfig(newConfig);
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
            <h1 className="text-3xl font-bold text-gray-900">
              Sistema de Detección Bluetooth
            </h1>
            <p className="text-gray-600 mt-1">
              Monitoreo en tiempo real
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <ConnectionStatus connected={wsConnected} />
            
            <TimeRangeSelector 
              onTimeRangeChange={handleTimeRangeChange}
              currentValue={timeConfig.value}
            />

            <button
              onClick={refresh}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Actualizar
            </button>
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
        
        <StatsCard
          title="Agentes Activos"
          value={devices.length}
          icon={<Activity className="w-6 h-6" />}
          color="purple"
          subtitle={devicesLoading ? 'Cargando...' : 'Raspberry Pi conectados'}
        />
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
          <h2 className="text-xl font-semibold mb-4">
            Dispositivos IoT ({devices.length})
          </h2>
          <DeviceList devices={devices} loading={devicesLoading} />
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
      </div>
    </div>
  );
};

export default Dashboard;