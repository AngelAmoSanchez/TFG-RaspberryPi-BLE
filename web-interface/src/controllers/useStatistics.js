import { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import ApiClient from '../models/ApiClient';
import { groupByZone, calculateZoneTotals } from '../models/StatisticsModel';

/**
 * Devuelve las estadísticas por hora
 * @param {Date} selectedDate - Fecha exacta
 * @param {number} refreshInterval - Intervalos de actualización en ms (por defecto puesto 30 segunfos)
 */
export function useHourlyStatistics(selectedDate = new Date(), refreshInterval = 30000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const dateStr = format(selectedDate, 'yyyy-MM-dd');
      const statistics = await ApiClient.getHourlyStatistics(dateStr);

      const groupedByZone = groupByZone(statistics);
      const totals = calculateZoneTotals(statistics);

      setData({ raw: statistics, byZone: groupedByZone, totals });
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('ERROR - Error obteniendo estadísticas por hora:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    fetchData();

    const intervalId = setInterval(fetchData, refreshInterval);

    return () => clearInterval(intervalId);
  }, [fetchData, refreshInterval]);

  return { data, loading, error, refresh: fetchData };
}

/**
 * Devuelve las estadísticas por cada día
 * @param {Date} startDate - Fecha de inicio del rango
 * @param {Date} endDate - Fecha de fin del rango
 */
export function useDailyStatistics(startDate, endDate) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const startStr = format(startDate, 'yyyy-MM-dd');
        const endStr = format(endDate, 'yyyy-MM-dd');

        const statistics = await ApiClient.getDailyStatistics(startStr, endStr);

        const groupedByZone = groupByZone(statistics);
        const totals = calculateZoneTotals(statistics);

        setData({ raw: statistics, byZone: groupedByZone, totals });
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('ERROR - Error obteniendo estadísticas por día:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [startDate, endDate]);

  return { data, loading, error };
}



/**
 * Devuelve las estadísticas en tiempo real (última hora)
 * @param {number} refreshInterval - Intervalo de actualización en ms (por defecto puesto 10 segundos)
*/
export function useCurrentSummary(refreshInterval = 10000) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await ApiClient.getCurrentSummary();
        setSummary(data);
        setLoading(false);
      } catch (err) {
        console.error('ERROR - Error obteniendo estadísticas en tiempo real:', err);
      }
    };

    fetchSummary();
    const intervalId = setInterval(fetchSummary, refreshInterval);
    return () => clearInterval(intervalId);
  }, [refreshInterval]);

  return { summary, loading };
}
