import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { useRealtimeStats } from '../useRealtimeStats';
import apiService from '../../services/api';
import websocketService from '../../services/websocket';
import { resolvePresetRequest } from '../../components/timePresets';

// Mock de servicios
vi.mock('../../services/api', () => ({
  default: {
    getRealtimeStats: vi.fn(),
    getRangeStats: vi.fn(),
  },
}));

vi.mock('../../services/websocket', () => ({
  default: {
    connect: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
  },
}));

vi.mock('../../components/timePresets', () => ({
  resolvePresetRequest: vi.fn(),
}));

describe('useRealtimeStats Hook', () => {
  const mockStats = {
    total: { unique_devices: 5, estimated_people: 3 },
    by_zone: { near: { unique_devices: 2 } }
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('debe cargar estadísticas en modo preset por defecto', async () => {
    apiService.getRealtimeStats.mockResolvedValue(mockStats);
    
    const config = { mode: 'preset', value: 5 };
    const { result } = renderHook(() => useRealtimeStats(config, false));

    await waitFor(() => {
      expect(apiService.getRealtimeStats).toHaveBeenCalledWith(5, '');
      expect(result.current.stats).toEqual(mockStats);
    });
  });

  test('debe usar getRangeStats cuando el modo es custom', async () => {
    apiService.getRangeStats.mockResolvedValue(mockStats);
    
    const config = { 
      mode: 'custom', 
      startDateTime: '2026-04-27T10:00:00', 
      endDateTime: '2026-04-27T11:00:00' 
    };
    
    renderHook(() => useRealtimeStats(config, false));

    await waitFor(() => {
      expect(apiService.getRangeStats).toHaveBeenCalledWith(
        '2026-04-27T10:00:00', 
        '2026-04-27T11:00:00', 
        ''
      );
    });
  });

  test('debe suscribirse a eventos de WebSocket si autoRefresh es true', () => {
    renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, true));

    expect(websocketService.connect).toHaveBeenCalled();
    expect(websocketService.on).toHaveBeenCalledWith('connection_status', expect.any(Function));
    expect(websocketService.on).toHaveBeenCalledWith('stats_update', expect.any(Function));
    expect(websocketService.on).toHaveBeenCalledWith('detection_event', expect.any(Function));
  });

  test('debe actualizar el estado cuando se recibe un stats_update (WebSocket callback)', async () => {
    const { result } = renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, true));

    // Función de callback registrada en el mock de websocketService.on
    const statsUpdateCallback = websocketService.on.mock.calls.find(call => call[0] === 'stats_update')[1];

    const newData = { data: { total: { unique_devices: 10 } } };
    
    act(() => {
      statsUpdateCallback(newData);
    });

    expect(result.current.stats).toEqual(newData.data);
  });

  test('no debe actualizar por WebSocket si el modo es custom', () => {
    const config = { mode: 'custom', startDateTime: '...', endDateTime: '...' };
    const { result } = renderHook(() => useRealtimeStats(config, true));

    const statsUpdateCallback = websocketService.on.mock.calls.find(call => call[0] === 'stats_update')[1];
    
    act(() => {
      statsUpdateCallback({ data: { some: 'data' } });
    });

    // stats sigue siendo null (o el valor inicial cargado por fetchStats) yaque no está en modo preset
    expect(result.current.stats).not.toEqual({ some: 'data' });
  });

  test('la función refresh debe forzar una nueva petición a la API', async () => {
    apiService.getRealtimeStats.mockResolvedValue(mockStats);
    const { result } = renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, false));

    await waitFor(() => expect(apiService.getRealtimeStats).toHaveBeenCalledTimes(1));

    await act(async () => {
      result.current.refresh();
    });

    expect(apiService.getRealtimeStats).toHaveBeenCalledTimes(2);
  });

  test('debe limpiar suscripciones al desmontar (cleanup)', () => {
    const { unmount } = renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, true));
    
    unmount();
    
    expect(websocketService.off).toHaveBeenCalledTimes(3);
  });

  test('debe capturar y establecer el mensaje de error cuando la API falla', async () => {
    const errorMessage = 'Error de conexión con el servidor';
    apiService.getRealtimeStats.mockRejectedValue(new Error(errorMessage));
    
    const { result } = renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, false));

    await waitFor(() => {
      expect(result.current.error).toBe(errorMessage);
      expect(result.current.loading).toBe(false);
    });
  });

  test('debe actualizar el estado wsConnected cuando cambia el estatus del WebSocket', () => {
    const { result } = renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, true));

    const connectionCallback = websocketService.on.mock.calls.find(call => call[0] === 'connection_status')[1];

    act(() => {
      connectionCallback({ connected: true });
    });
    expect(result.current.wsConnected).toBe(true);

    act(() => {
      connectionCallback({ connected: false });
    });
    expect(result.current.wsConnected).toBe(false);
  });

  test('debe disparar fetchStats cuando se recibe un evento de detección en modo preset', async () => {
    apiService.getRealtimeStats.mockResolvedValue(mockStats);
    
    renderHook(() => useRealtimeStats({ mode: 'preset', value: 5 }, true));

    await waitFor(() => expect(apiService.getRealtimeStats).toHaveBeenCalledTimes(1));

    const detectionCallback = websocketService.on.mock.calls.find(call => call[0] === 'detection_event')[1];

    await act(async () => {
      detectionCallback();
    });

    expect(apiService.getRealtimeStats).toHaveBeenCalledTimes(2);
  });

  test('debe usar getRealtimeStats(5) si el presetKey es desconocido', async () => {
    resolvePresetRequest.mockReturnValue(null);
    apiService.getRealtimeStats.mockResolvedValue(mockStats);

    const config = { mode: 'preset', presetKey: 'unknown-key' };
    renderHook(() => useRealtimeStats(config, false));

    await waitFor(() => {
      expect(apiService.getRealtimeStats).toHaveBeenCalledWith(5, '');
    });
  });

  test('debe usar getRealtimeStats con los minutos del presetKey si el tipo es minutes', async () => {
    resolvePresetRequest.mockReturnValue({ type: 'minutes', minutes: 30 });
    apiService.getRealtimeStats.mockResolvedValue(mockStats);

    const config = { mode: 'preset', presetKey: 'last-30' };
    renderHook(() => useRealtimeStats(config, false));

    await waitFor(() => {
      expect(apiService.getRealtimeStats).toHaveBeenCalledWith(30, '');
    });
  });

  test('debe usar getRangeStats con el rango del presetKey si el tipo es range', async () => {
    resolvePresetRequest.mockReturnValue({
      type: 'range',
      startDateTime: '2026-05-17T00:00:00',
      endDateTime: '2026-05-17T23:59:59'
    });
    apiService.getRangeStats.mockResolvedValue(mockStats);

    const config = { mode: 'preset', presetKey: 'today' };
    renderHook(() => useRealtimeStats(config, false));

    await waitFor(() => {
      expect(apiService.getRangeStats).toHaveBeenCalledWith(
        '2026-05-17T00:00:00',
        '2026-05-17T23:59:59',
        ''
      );
    });
  });

  test('debe disparar fetchStats en lugar de setStats directo por WebSocket si hay presetKey', async () => {
    apiService.getRealtimeStats.mockResolvedValue(mockStats);
    const config = { mode: 'preset', presetKey: 'dynamic-preset' };
    
    resolvePresetRequest.mockReturnValue({ type: 'minutes', minutes: 10 });
    
    renderHook(() => useRealtimeStats(config, true));

    await waitFor(() => expect(apiService.getRealtimeStats).toHaveBeenCalledTimes(1));

    const statsUpdateCallback = websocketService.on.mock.calls.find(call => call[0] === 'stats_update')[1];
    
    const wsData = { data: { total: { unique_devices: 99 } } };

    await act(async () => {
      statsUpdateCallback(wsData);
    });

    expect(apiService.getRealtimeStats).toHaveBeenCalledTimes(2);
  });
});