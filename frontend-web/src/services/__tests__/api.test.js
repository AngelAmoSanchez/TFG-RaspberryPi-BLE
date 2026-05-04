import { describe, test, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import apiService from '../api';

// Mock  de axios para interceptores y métodos HTTP
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: { headers: { common: {} } }
  };
  return { default: mockAxios };
});

describe('ApiService', () => {
  let service;

  beforeEach(() => {
    vi.clearAllMocks();
    service = apiService;
    localStorage.clear();
  });

  test('debe obtener detecciones recientes y recuentos con filtros', async () => {
    service.client.get.mockResolvedValue({ data: [] });

    await service.getRecentDetections(50, 'near');
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/detections/recent', {
      params: { limit: 50, zone: 'near' }
    });

    await service.getDetectionCount(12, 'medium');
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/detections/count', {
      params: { hours: 12, zone: 'medium' }
    });
  });

  test('debe gestionar estadísticas en tiempo real, horarias y diarias', async () => {
    service.client.get.mockResolvedValue({ data: {} });

    await service.getRealtimeStats(10, 'sensor-01');
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/statistics/realtime', {
      params: { minutes: 10, device_id: 'sensor-01' }
    });

    await service.getHourlyStats('2026-04-28');
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/statistics/hourly', {
      params: { date: '2026-04-28' }
    });

    await service.getDailyStats('2026-04-01', '2026-04-07');
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/statistics/daily', {
      params: { start_date: '2026-04-01', end_date: '2026-04-07' }
    });
  });

  test('debe verificar salud del sistema y gestionar umbrales', async () => {
    service.client.get.mockResolvedValue({ data: { status: 'ok' } });
    service.client.post.mockResolvedValue({ data: { success: true } });

    const health = await service.checkHealth();
    expect(health.status).toBe('ok');

    await service.getThresholds();
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/settings/thresholds');

    await service.resetThresholds();
    expect(service.client.post).toHaveBeenCalledWith('/api/v1/settings/thresholds/reset');
  });

  test('debe manejar parámetros de tiempo correctamente para estadísticas', async () => {
    service.client.get.mockResolvedValue({ data: { stats: [] } });
    
    await service.getDeviceStats('dev_test');
    
    expect(service.client.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/devices/dev_test/stats')
    );
  });

  test('getDevices debe manejar correctamente su ruta', async () => {
    service.client.get.mockResolvedValue({ data: [] });
    
    await service.getDevices(true);
    
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/devices/', {
      params: { active_only: true }
    });
  });

  test('debe obtener estadísticas y registrar dispositivos', async () => {
    service.client.get.mockResolvedValue({ data: {} });
    service.client.post.mockResolvedValue({ data: { id: 1 } });

    await service.getDeviceStats('dev_123');
    expect(service.client.get).toHaveBeenCalledWith('/api/v1/devices/dev_123/stats');

    const newDevice = { device_id: 'new', name: 'Sensor' };
    await service.registerDevice(newDevice);
    expect(service.client.post).toHaveBeenCalledWith('/api/v1/devices/register', newDevice);
  });

  test('checkHealth debe devolver error formateado en el catch', async () => {
    // Fallo de red simulado
    service.client.get.mockRejectedValue(new Error('Backend Offline'));
    
    const health = await service.checkHealth();
    
    expect(health).toEqual({
      status: 'error',
      message: 'Backend Offline'
    });
  });

  test('debe obtener información básica de la API', async () => {
    service.client.get.mockResolvedValue({ data: { version: '1.0' } });
    await service.getApiInfo();
    expect(service.client.get).toHaveBeenCalledWith('/');
  });

  test('debe actualizar y resetear umbrales de zona', async () => {
    service.client.put.mockResolvedValue({ data: { success: true } });
    service.client.post.mockResolvedValue({ data: { success: true } });

    await service.updateThresholds(-40, -70);
    expect(service.client.put).toHaveBeenCalledWith('/api/v1/settings/thresholds', {
      near_threshold: -40,
      medium_threshold: -70
    });

    await service.resetThresholds();
    expect(service.client.post).toHaveBeenCalledWith('/api/v1/settings/thresholds/reset');
  });

  test('el cliente debe estar configurado para peticiones de tipo blob', async () => {
    service.client.get.mockResolvedValue({ data: new Blob() });
    
    await service.client.get('/api/v1/export/detections/csv', {
      responseType: 'blob',
      headers: { 'Accept': 'text/csv' }
    });
    
    expect(service.client.get).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ responseType: 'blob' })
    );
  });

  test('getHistogramStats debe obtener el histograma con parámetros por defecto', async () => {
    const mockData = { range: 'hour', buckets: [] };
    service.client.get.mockResolvedValue({ data: mockData });

    const result = await service.getHistogramStats();

    expect(service.client.get).toHaveBeenCalledWith('/api/v1/statistics/histogram', {
      params: { range: 'hour' }
    });
    expect(result).toEqual(mockData);
  });

  test('getHistogramStats debe incluir el device_id en los parámetros si se proporciona', async () => {
    service.client.get.mockResolvedValue({ data: {} });

    await service.getHistogramStats('today', 'raspberry-pi-01');

    expect(service.client.get).toHaveBeenCalledWith('/api/v1/statistics/histogram', {
      params: { 
        range: 'today', 
        device_id: 'raspberry-pi-01' 
      }
    });
  });

  test('getHistogramStats debe funcionar correctamente con el rango "week"', async () => {
    service.client.get.mockResolvedValue({ data: {} });

    await service.getHistogramStats('week');

    expect(service.client.get).toHaveBeenCalledWith('/api/v1/statistics/histogram', {
      params: { range: 'week' }
    });
  });
});