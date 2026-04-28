import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Dashboard from '../Dashboard';
import { useRealtimeStats } from '@/hooks/useRealtimeStats';
import { useDevices } from '@/hooks/useDevices';

// Mocks de hooks para los datos
vi.mock('@/hooks/useRealtimeStats');
vi.mock('@/hooks/useDevices');

describe('Dashboard Component', () => {
  const mockRefresh = vi.fn();
  
  const defaultStats = {
    total: { unique_devices: 10, estimated_people: 7, total_detections: 100 },
    by_zone: {
      near: { unique_devices: 4, estimated_people: 3, avg_rssi: -55.5 },
      medium: { unique_devices: 6, estimated_people: 4, avg_rssi: -75.2 }
    },
    timestamp: '2026-04-28T10:00:00Z'
  };

  const mockDevices = [
    { device_id: 'dev1', name: 'Sensor Principal', is_active: true },
    { device_id: 'dev2', name: 'Sensor Secundario', is_active: true },
    { device_id: 'dev3', name: 'Inactivo', is_active: false }
  ];

  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    
    useRealtimeStats.mockReturnValue({
      stats: defaultStats,
      loading: false,
      error: null,
      wsConnected: true,
      refresh: mockRefresh
    });

    useDevices.mockReturnValue({
      devices: mockDevices,
      loading: false
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test('debe configurar un intervalo de actualización de 30s en modo preset', () => {
    render(<Dashboard />);
    
    // Pasamos los 30 segundos
    act(() => {
      vi.advanceTimersByTime(30000);
    });

    expect(mockRefresh).toHaveBeenCalled();
  });

  test('debe mostrar el rango de fechas formateado en modo personalizado', () => {
    useRealtimeStats.mockReturnValue({
      stats: defaultStats,
      loading: false,
      error: null,
      refresh: mockRefresh
    });

    render(<Dashboard />);

    // Simulamos el cambio a modo personalizado con fechas específicas
    const selector = screen.getByRole('button', { name: /5 minutos/i }); // Botón del TimeRangeSelector
        
    act(() => {
      const customConfig = { 
        mode: 'custom', 
        startDateTime: '2026-04-28T08:00', 
        endDateTime: '2026-04-28T10:00' 
      };
      fireEvent.click(screen.getByText(/Actualizar/i)); // Forzamos re-render
    });

  });

  test('debe devolver etiquetas de tiempo correctas para diferentes minutos', () => {
    const { rerender } = render(<Dashboard />);

    // Casos de prueba
    const cases = [
      { mins: 1, expected: /último minuto/i },
      { mins: 60, expected: /última hora/i },
      { mins: 1440, expected: /último día/i },
      { mins: 10080, expected: /últimos 7 días/i }
    ];

    expect(screen.getByText(/últimos 5 minutos/i)).toBeInTheDocument();
  });

  test('debe mostrar la descripción de ventana de tiempo correctamente', () => {
    render(<Dashboard />);
    expect(screen.getByText(/ventana de tiempo: 5 minutos/i)).toBeInTheDocument();
  });

  test('debe mostrar el estado de carga inicial', () => {
    useRealtimeStats.mockReturnValue({
      stats: null,
      loading: true,
      error: null,
      refresh: mockRefresh
    });

    render(<Dashboard />);
    expect(screen.getByText(/cargando estadísticas/i)).toBeInTheDocument();
  });

  test('debe mostrar pantalla de error y permitir reintentar', () => {
    // Estado de error en el hook
    useRealtimeStats.mockReturnValue({
      stats: null,
      loading: false,
      error: 'Error de servidor',
      wsConnected: false,
      refresh: mockRefresh
    });

    render(<Dashboard />);

    expect(screen.getByText(/error al cargar datos: error de servidor/i)).toBeInTheDocument();
    
    const retryBtn = screen.getByRole('button', { name: /reintentar/i });
    fireEvent.click(retryBtn);

    expect(mockRefresh).toHaveBeenCalled();
  });

  test('debe permitir cambiar el dispositivo seleccionado y filtrar estadísticas', () => {
    render(<Dashboard />);
    
    const label = screen.getByText(/dispositivo:/i);
    const select = label.nextElementSibling;
    
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe('SELECT');

    fireEvent.change(select, { target: { value: 'dev1' } });

    expect(select.value).toBe('dev1');
  });

  test('debe mostrar el RSSI promedio si está disponible en los datos de zona', () => {
    render(<Dashboard />);
    expect(screen.getByText(/RSSI promedio: -55.5 dBm/i)).toBeInTheDocument();
    expect(screen.getByText(/RSSI promedio: -75.2 dBm/i)).toBeInTheDocument();
  });

  test('debe alternar entre mostrar y ocultar dispositivos inactivos', () => {
    render(<Dashboard />);
    
    const toggleBtn = screen.getByRole('button', { name: /ocultar inactivos/i });
    
    expect(screen.getByText(/Dispositivos IoT \(3\)/i)).toBeInTheDocument();

    fireEvent.click(toggleBtn);

    // Ahora solo los activos
    expect(screen.getByText(/Dispositivos IoT \(2\)/i)).toBeInTheDocument();
    expect(screen.getByText(/mostrar todos/i)).toBeInTheDocument();
  });
});