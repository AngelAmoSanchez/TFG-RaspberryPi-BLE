import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../services/api';
import websocketService from '../services/websocket';

export const useRealtimeStats = (timeConfig = { mode: 'preset', value: 5 }, autoRefresh = true) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  const modeRef = useRef(timeConfig.mode);
  
  useEffect(() => {
    modeRef.current = timeConfig.mode;
  }, [timeConfig.mode]);

  const { mode, value, startDate, endDate, startDateTime, endDateTime } = timeConfig;

  // Busca las estadísticas en tiempo real
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      let data;
      
      if (mode === 'custom' && startDateTime && endDateTime) {
        // Usar rango personalizado (fecha y hora) 
        console.log('Buscando estadísticas para el rango personalizado:', {
          start: startDateTime,
          end: endDateTime
        });
        
        data = await apiService.getRangeStats(startDateTime, endDateTime);
        
      } else {
        const minutes = value || 5;
        console.log(`Buscando estadísticas para los últimos ${minutes} minutos...`);
        
        data = await apiService.getRealtimeStats(minutes);
      }
      
      setStats(data);
    } catch (err) {
      setError(err.message);
      console.error('ERROR - Error obteniendo estadísticas:', err);
    } finally {
      setLoading(false);
    }
  }, [mode, value, startDate, endDate, startDateTime, endDateTime]);

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
      // Solo actualiza si estamos en modo preset, para evitar sobrescribir datos personalizados
      if (modeRef.current === 'preset') {
        setStats(data.data);
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
  }, [autoRefresh]);

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