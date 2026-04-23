import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';
import websocketService from '../services/websocket';

export const useRealtimeStats = (timeConfig = { mode: 'preset', value: 5 }, autoRefresh = true) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  const { mode, value, startDate, endDate } = timeConfig;

  // Busca las estadísticas en tiempo real
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      let data;
      if (mode === 'custom' && startDate && endDate) {
        data = await apiService.getDailyStats(startDate, endDate);
        
        // Transformar los datos diarios al formato esperado por el dashboard
        const transformedStats = {
          timestamp: new Date().toISOString(),
          time_window_minutes: 0,
          total: {
            unique_devices: 0,
            total_detections: 0,
            estimated_people: 0,
            avg_rssi: null
          },
          by_zone: {}
        };

        // Añadir lógica para transformar los datos diarios en el formato esperado por el dashboard
        if (data.statistics && Array.isArray(data.statistics)) {
          data.statistics.forEach(dayStat => {
            if (dayStat.by_zone) {
              Object.entries(dayStat.by_zone).forEach(([zone, zoneData]) => {
                if (!transformedStats.by_zone[zone]) {
                  transformedStats.by_zone[zone] = {
                    unique_devices: 0,
                    total_detections: 0,
                    estimated_people: 0,
                    avg_rssi: []
                  };
                }
                
                transformedStats.by_zone[zone].unique_devices += zoneData.unique_devices || 0;
                transformedStats.by_zone[zone].total_detections += zoneData.total_detections || 0;
                transformedStats.by_zone[zone].estimated_people += zoneData.estimated_people || 0;
                
                if (zoneData.avg_rssi) {
                  transformedStats.by_zone[zone].avg_rssi.push(zoneData.avg_rssi);
                }
              });
            }
            
            transformedStats.total.unique_devices += dayStat.total?.unique_devices || 0;
            transformedStats.total.total_detections += dayStat.total?.total_detections || 0;
            transformedStats.total.estimated_people += dayStat.total?.estimated_people || 0;
          });
          
          // Calcular el promedio de RSSI por zona
          Object.keys(transformedStats.by_zone).forEach(zone => {
            const rssiValues = transformedStats.by_zone[zone].avg_rssi;
            if (rssiValues.length > 0) {
              transformedStats.by_zone[zone].avg_rssi = 
                rssiValues.reduce((a, b) => a + b, 0) / rssiValues.length;
            } else {
              transformedStats.by_zone[zone].avg_rssi = null;
            }
          });
        }
        
        data = transformedStats;
      } else {
        // Usar minutos predeterminados
        const minutes = value || 5;
        data = await apiService.getRealtimeStats(minutes);
      }
      
      setStats(data);
    } catch (err) {
      setError(err.message);
      console.error('ERROR - Error obteniendo estadísticas en tiempo real:', err);
    } finally {
      setLoading(false);
    }
  }, [mode, value, startDate, endDate]);

  // Carga inicial y recarga cuando cambian los parámetros
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Configura WebSocket
  useEffect(() => {
    if (!autoRefresh) return;

    // Conecta con WebSocket
    websocketService.connect();

    // Escucha cambios en la conexión
    const handleConnectionStatus = (status) => {
      setWsConnected(status.connected);
    };

    // Escucha actualizaciones de estadísticas
    const handleStatsUpdate = (data) => {
      console.log('Actualización de estadísticas recibida por WebSocket:', data);
      // Solo actualiza si estamos en modo preset, para evitar sobrescribir datos personalizados
      if (mode === 'preset') {
        setStats(data.data);
      }
    };

    // Escucha eventos de detección (dispara actualización)
    const handleDetectionEvent = () => {
      console.log('Evento de detección recibido, actualizando estadísticas...');
      if (mode === 'preset') {
        fetchStats();
      }
    };

    // Suscribe a eventos
    websocketService.on('connection_status', handleConnectionStatus);
    websocketService.on('stats_update', handleStatsUpdate);
    websocketService.on('detection_event', handleDetectionEvent);

    // Cleanup
    return () => {
      websocketService.off('connection_status', handleConnectionStatus);
      websocketService.off('stats_update', handleStatsUpdate);
      websocketService.off('detection_event', handleDetectionEvent);
    };
  }, [autoRefresh, fetchStats, mode]);

  // Función para forzar actualización manual
  const refresh = useCallback(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    wsConnected,
    refresh
  };
};