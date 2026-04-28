import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDevices } from '../useDevices';
import apiService from '@/services/api';

// Mock del servicio API
vi.mock('@/services/api', () => {
  const mockMethods = {
    getDevices: vi.fn(),
    getDeviceStats: vi.fn(),
    registerDevice: vi.fn(),
  };
  return {
    default: mockMethods,
    apiService: mockMethods,
  };
});

describe('useDevices Hook', () => {
  const mockDevices = [{ device_id: 'dev_1', name: 'Sensor A', is_active: true }];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test('debe cargar dispositivos exitosamente al inicializar', async () => {
    apiService.getDevices.mockResolvedValue(mockDevices);

    const { result } = renderHook(() => useDevices(false));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.devices).toEqual(mockDevices);
      expect(result.current.loading).toBe(false);
    }, { timeout: 4000 });
  });

  test('debe manejar errores en la carga inicial', async () => {
    const errorMsg = 'Error API';
    // Forzamos el rechazo con el mensaje
    apiService.getDevices.mockRejectedValue(new Error(errorMsg));

    const { result } = renderHook(() => useDevices(false));

    await waitFor(() => {
      expect(result.current.error).toBe(errorMsg);
      expect(result.current.loading).toBe(false);
    }, { timeout: 2000 });
  });

  test('registerDevice debe añadir el nuevo dispositivo al estado local', async () => {
    apiService.getDevices.mockResolvedValue([]);
    const newDevice = { device_id: 'new_id', name: 'New' };
    apiService.registerDevice.mockResolvedValue(newDevice);

    const { result } = renderHook(() => useDevices());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      const added = await result.current.registerDevice(newDevice);
      expect(added).toEqual(newDevice);
    });

    expect(result.current.devices).toContainEqual(newDevice);
  });

  test('getDeviceStats debe retornar datos exitosamente', async () => {
    const mockStats = { uptime: '100%' };
    apiService.getDeviceStats.mockResolvedValue(mockStats);

    const { result } = renderHook(() => useDevices());
    
    let stats;
    await act(async () => {
      stats = await result.current.getDeviceStats('dev_1');
    });

    expect(stats).toEqual(mockStats);
  });

  test('debe limpiar el intervalo al desmontar (cleanup)', async () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() => useDevices(false));
    
    // Al desmontar se ejecuta clearInterval
    unmount();
    
    expect(vi.getTimerCount()).toBe(0);
  });
});