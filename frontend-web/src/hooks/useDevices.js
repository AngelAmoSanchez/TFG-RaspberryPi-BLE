import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

export const useDevices = (activeOnly = false) => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Busca los dispositivos
  const fetchDevices = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDevices(activeOnly);
      setDevices(data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching devices:', err);
    } finally {
      setLoading(false);
    }
  }, [activeOnly]);

  // Carga inicial
  useEffect(() => {
    fetchDevices();
    
    // Auto-refresh cada 30 segundos
    const interval = setInterval(fetchDevices, 30000);
    
    return () => clearInterval(interval);
  }, [fetchDevices]);

  // Obtiene estadísticas de un dispositivo
  const getDeviceStats = useCallback(async (deviceId) => {
    try {
      const stats = await apiService.getDeviceStats(deviceId);
      return stats;
    } catch (err) {
      console.error(`ERROR - Error obteniendo estadísticas para el dispositivo ${deviceId}:`, err);
      throw err;
    }
  }, []);

  // Registra un nuevo dispositivo
  const registerDevice = useCallback(async (deviceData) => {
    try {
      const newDevice = await apiService.registerDevice(deviceData);
      setDevices(prev => [...prev, newDevice]);
      return newDevice;
    } catch (err) {
      console.error('ERROR - Error registrando dispositivo:', err);
      throw err;
    }
  }, []);

  return {
    devices,
    loading,
    error,
    refresh: fetchDevices,
    getDeviceStats,
    registerDevice
  };
};
