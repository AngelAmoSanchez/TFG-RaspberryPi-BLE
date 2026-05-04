import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../services/api';
import websocketService from '../services/websocket';
import { resolvePresetRequest } from '../components/timePresets';

export const useRealtimeStats = (timeConfig = { mode: 'preset', value: 5 }, autoRefresh = true, deviceId = '') => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  const modeRef = useRef(timeConfig.mode);
  const deviceIdRef = useRef(deviceId);

  useEffect(() => {
    modeRef.current = timeConfig.mode;
  }, [timeConfig.mode]);

  useEffect(() => {
    deviceIdRef.current = deviceId;
  }, [deviceId]);

  const { mode, value, presetKey, startDate, endDate, startDateTime, endDateTime } = timeConfig;

  // Busca las estadísticas en tiempo real
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let data;
      
      const currentDeviceId = deviceIdRef.current;

      if (mode === 'custom' && startDateTime && endDateTime) {
        // Usar rango personalizado (fecha y hora) 
        console.log('Buscando estadísticas para el rango personalizado:', {
          start: startDateTime,
          end: endDateTime,
          deviceId: currentDeviceId || 'todos'
        });
        
        data = await apiService.getRangeStats(startDateTime, endDateTime, currentDeviceId);
      } else if (presetKey) {
        // Preset identificado por presetKey
        const request = resolvePresetRequest(presetKey);

        if (!request) {
          console.warn(`Preset desconocido: ${presetKey}, usando últimos 5 minutos`);
          data = await apiService.getRealtimeStats(5, currentDeviceId);
        } else if (request.type === 'minutes') {
          console.log(
            `Buscando estadísticas (preset ${presetKey}) para los últimos ${request.minutes} minutos...`
          );
          data = await apiService.getRealtimeStats(request.minutes, currentDeviceId);
        } else if (request.type === 'range') {
          // 'today' o 'yesterday' -> recalculado en cada fetch
          console.log(`Buscando estadísticas (preset ${presetKey}) en rango:`, request);
          data = await apiService.getRangeStats(
            request.startDateTime,
            request.endDateTime,
            currentDeviceId
          );
        }
      } else {
        const minutes = value || 5;
        console.log(`Buscando estadísticas para los últimos ${minutes} minutos...`, {
          deviceId: currentDeviceId || 'todos'
        });
        
        data = await apiService.getRealtimeStats(minutes, currentDeviceId);
      }

      setStats(data);
    } catch (err) {
      setError(err.message);
      console.error('ERROR - Error obteniendo estadísticas:', err);
    } finally {
      setLoading(false);
    }
  }, [mode, value, presetKey, startDate, endDate, startDateTime, endDateTime, deviceId]);

  // Carga inicial y recarga cuando cambian los parámetros
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Configura WebSocket
  useEffect(() => {
    if (!autoRefresh) return;

    console.log('Configurando conexión WebSocket...');

    // Conecta con WebSocket
    websocketService.connect();

    // Escucha cambios en la conexión
    const handleConnectionStatus = (status) => {
      console.log('Estado de la conexión WebSocket:', status.connected);
      setWsConnected(status.connected);
    };

    // Escucha actualizaciones de estadísticas
    const handleStatsUpdate = (data) => {
      console.log('Actualización de estadísticas recibida via WebSocket:', data);
      // Solo actualiza si estamos en modo preset y el preset no tiene un rango fijo (como 'today'), para evitar
      if (modeRef.current === 'preset' && !presetKey) {
        setStats(data.data);
      } else if (modeRef.current === 'preset' && presetKey) {
        fetchStats();
      }
    };

    // Escucha eventos de detección (dispara actualización)
    const handleDetectionEvent = () => {
      console.log('Evento de detección recibido');
      // Solo actualiza si estamos en modo preset
      if (modeRef.current === 'preset') {
        fetchStats();
      }
    };

    // Suscribe a eventos
    websocketService.on('connection_status', handleConnectionStatus);
    websocketService.on('stats_update', handleStatsUpdate);
    websocketService.on('detection_event', handleDetectionEvent);

    // Cleanup
    return () => {
      console.log('Limpieza de eventos de WebSocket...');
      websocketService.off('connection_status', handleConnectionStatus);
      websocketService.off('stats_update', handleStatsUpdate);
      websocketService.off('detection_event', handleDetectionEvent);
    };
  }, [autoRefresh, presetKey, fetchStats]);

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