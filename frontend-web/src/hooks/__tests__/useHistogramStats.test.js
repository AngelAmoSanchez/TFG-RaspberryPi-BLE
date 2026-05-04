import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { useHistogramStats } from '../useHistogramStats';
import apiService from '../../services/api';
import websocketService from '../../services/websocket';

// Mock de servicios
vi.mock('../../services/api', () => ({
  default: {
    getHistogramStats: vi.fn(),
  },
}));

vi.mock('../../services/websocket', () => ({
  default: {
    on: vi.fn(),
    off: vi.fn(),
  },
}));

describe('useHistogramStats Hook', () => {
  const mockHistogramData = {
    range: 'hour',
    bin_interval: '10 minutes',
    buckets: [
      { period_start: '2026-05-17T10:00:00', total: 5, by_zone: { near: 2, medium: 2, far: 1 } }
    ]
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Importante: No activamos fake timers globalmente para evitar el ReferenceError en el cleanup
    apiService.getHistogramStats.mockResolvedValue(mockHistogramData);
  });

  afterEach(() => {
    // Si un test activó fake timers, los restauramos aquí de forma segura
    if (vi.isFakeTimers()) {
      vi.clearAllTimers();
      vi.useRealTimers();
    }
  });

  test('debe cargar datos iniciales correctamente con parámetros por defecto', async () => {
    const { result } = renderHook(() => useHistogramStats());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(apiService.getHistogramStats).toHaveBeenCalledWith('hour', '');
      expect(result.current.data).toEqual(mockHistogramData);
      expect(result.current.loading).toBe(false);
    });
  });

  test('debe reaccionar a cambios en el parámetro range', async () => {
    const { rerender } = renderHook(({ range }) => useHistogramStats(range), {
      initialProps: { range: 'hour' }
    });

    await waitFor(() => expect(apiService.getHistogramStats).toHaveBeenCalledWith('hour', ''));

    // Cambiamos a rango 'today'
    rerender({ range: 'today' });

    await waitFor(() => {
      expect(apiService.getHistogramStats).toHaveBeenCalledWith('today', '');
    });
  });

  test('debe configurar un intervalo de refresco automático de 30s', async () => {
    vi.useFakeTimers(); 
    renderHook(() => useHistogramStats('hour', true));

    // CORRECCIÓN: Usamos advanceTimersByTimeAsync(0) para resolver solo las promesas 
    // de la carga inicial (Línea 38) sin activar el cronómetro del intervalo.
    await vi.advanceTimersByTimeAsync(0); 
    expect(apiService.getHistogramStats).toHaveBeenCalledTimes(1);

    // Ahora avanzamos manualmente los 30 segundos para disparar el refresco (Línea 47)
    await act(async () => {
      vi.advanceTimersByTime(30000);
    });

    expect(apiService.getHistogramStats).toHaveBeenCalledTimes(2);
  });

  test('debe refrescar los datos al recibir un evento de detección (WebSocket) con throttling', async () => {
    vi.useFakeTimers();
    renderHook(() => useHistogramStats('hour', true));

    // Esperamos a que termine el fetch inicial (Línea 38)
    await vi.advanceTimersByTimeAsync(0);
    expect(apiService.getHistogramStats).toHaveBeenCalledTimes(1);

    const handleDetectionEvent = websocketService.on.mock.calls.find(
      (call) => call[0] === 'detection_event'
    )[1];

    // Primer evento: Debe disparar la carga (now - 0 > 5000) (Línea 58)
    await act(async () => {
      handleDetectionEvent();
    });
    expect(apiService.getHistogramStats).toHaveBeenCalledTimes(2);

    // Segundo evento inmediato: Debe ser ignorado por el throttling de 5s (Línea 58)
    await act(async () => {
      handleDetectionEvent();
    });
    expect(apiService.getHistogramStats).toHaveBeenCalledTimes(2);

    // Avanzamos 6 segundos para superar el límite del throttle (Línea 58)
    await act(async () => {
      vi.advanceTimersByTime(6000);
      handleDetectionEvent();
    });

    expect(apiService.getHistogramStats).toHaveBeenCalledTimes(3);
  });

  test('debe manejar errores de la API correctamente', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    apiService.getHistogramStats.mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useHistogramStats());

    await waitFor(() => {
      expect(result.current.error).toBe('API Error');
    });
    
    // Verifica log de error de la línea 31 de useHistogramStats.js
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('ERROR - Histograma:'), expect.any(Error));
  });

  test('debe limpiar el intervalo y el listener de WebSocket al desmontar', () => {
    // Espiamos el clearInterval global para verificar la línea 48
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval');
    const { unmount } = renderHook(() => useHistogramStats('hour', true));

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    // Verifica cleanup de la línea 63
    expect(websocketService.off).toHaveBeenCalledWith('detection_event', expect.any(Function));
  });
});