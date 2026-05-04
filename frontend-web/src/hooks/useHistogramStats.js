import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../services/api';
import websocketService from '../services/websocket';

/**
 * Hook que obtiene los datos del histograma agrupado por intervalos.
 *
 * range: 'hour'  -> 6 barras de 10min (la hora actual de reloj)
 *        'today' -> 8 barras de 3h (00-03, 03-06, ..., 21-24)
 *        'week'  -> 7 barras de 1 día (los últimos 7 días terminando hoy)
 */
export const useHistogramStats = (range = 'hour', autoRefresh = true, deviceId = '') => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const deviceIdRef = useRef(deviceId);
  useEffect(() => {
    deviceIdRef.current = deviceId;
  }, [deviceId]);

  const fetchHistogram = useCallback(async () => {
    try {
      setError(null);
      const response = await apiService.getHistogramStats(range, deviceIdRef.current);
      setData(response);
    } catch (err) {
      console.error('ERROR - Histograma:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [range]);

  // Carga inicial y cambio de rango
  useEffect(() => {
    setLoading(true);
    fetchHistogram();
  }, [fetchHistogram]);

  // Refresco periódico cada 30s
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      console.log(`Refrescando histograma (${range})...`);
      fetchHistogram();
    }, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, range, fetchHistogram]);

  // WebSocket refresca al recibir nuevas detecciones 
  useEffect(() => {
    if (!autoRefresh) return;

    let lastFetch = 0;
    const handleDetectionEvent = () => {
      const now = Date.now();
      // Máximo 1 refresh cada 5s desde eventos WS para no saturar
      if (now - lastFetch > 5000) {
        lastFetch = now;
        fetchHistogram();
      }
    };

    websocketService.on('detection_event', handleDetectionEvent);
    return () => websocketService.off('detection_event', handleDetectionEvent);
  }, [autoRefresh, fetchHistogram]);

  return { data, loading, error, refresh: fetchHistogram };
};
