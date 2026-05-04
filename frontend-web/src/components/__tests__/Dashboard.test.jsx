import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Dashboard from '../Dashboard';
import { useRealtimeStats } from '@/hooks/useRealtimeStats';
import { useDevices } from '@/hooks/useDevices';
import * as timePresets from '../timePresets';

// Mocks de hooks para los datos
vi.mock('@/hooks/useRealtimeStats');
vi.mock('@/hooks/useDevices');

// Mock del nuevo componente HistogramChart
vi.mock('../HistogramChart', () => ({
  default: ({ deviceId }) => (
    <div data-testid="histogram-chart">
      Histogram Chart {deviceId ? `for ${deviceId}` : 'all devices'}
    </div>
  )
}));

// Mock de la lógica de presets
vi.mock('../timePresets', () => ({
  DEFAULT_PRESET_KEY: 'last-5-mins',
  getPresetByKey: vi.fn(),
  getPresetLabel: vi.fn(),
}));

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
    
    // Configuración por defecto de los mocks
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

    timePresets.getPresetLabel.mockReturnValue('Últimos 5 minutos');
    timePresets.getPresetByKey.mockReturnValue({ kind: 'rolling-minutes', minutes: 5 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test('debe renderizar los componentes principales incluyendo el nuevo HistogramChart', () => {
    render(<Dashboard />);
    expect(screen.getByText(/Sistema de Detección Bluetooth/i)).toBeInTheDocument();
    expect(screen.getByTestId('histogram-chart')).toBeInTheDocument();
    expect(screen.getByText(/Distribución por Zonas/i)).toBeInTheDocument();
  });

  test('debe configurar un intervalo de actualización de 30s en modo preset', () => {
    render(<Dashboard />);
    
    // Pasamos los 30 segundos
    act(() => {
      vi.advanceTimersByTime(30000);
    });

    expect(mockRefresh).toHaveBeenCalled();
  });

  test('debe mostrar la etiqueta correcta cuando hay un presetKey seleccionado', () => {
    timePresets.getPresetLabel.mockReturnValue('Hoy');
    render(<Dashboard />);
    expect(screen.getByText(/Monitoreo en tiempo real • Hoy/i)).toBeInTheDocument();
  });

  test('debe mostrar el rango de fechas formateado en modo personalizado', () => {
    useRealtimeStats.mockImplementation((config) => ({
      stats: defaultStats,
      loading: false,
      error: null,
      refresh: mockRefresh
    }));

    render(<Dashboard />);
  });

  test('debe mostrar la descripción correcta para el preset "Hoy" (kind: today)', () => {
    timePresets.getPresetByKey.mockReturnValue({ kind: 'today' });
    render(<Dashboard />);
    expect(screen.getByText(/desde las 00:00 de hoy/i)).toBeInTheDocument();
  });

  test('debe mostrar la descripción correcta para el preset "Ayer" (kind: yesterday)', () => {
    timePresets.getPresetByKey.mockReturnValue({ kind: 'yesterday' });
    render(<Dashboard />);
    expect(screen.getByText(/todo el día de ayer/i)).toBeInTheDocument();
  });

  test('debe gestionar correctamente las descripciones de ventana para rolling-minutes (horas/días)', () => {
    // Caso de horas
    timePresets.getPresetByKey.mockReturnValue({ kind: 'rolling-minutes', minutes: 120 });
    const { rerender } = render(<Dashboard />);
    expect(screen.getByText(/Ventana de tiempo: 2 horas/i)).toBeInTheDocument();

    // Caso de días
    timePresets.getPresetByKey.mockReturnValue({ kind: 'rolling-minutes', minutes: 2880 });
    rerender(<Dashboard />);
    expect(screen.getByText(/Ventana de tiempo: 2 días/i)).toBeInTheDocument();
  });

  test('debe mostrar estado de carga y error correctamente', () => {
    useRealtimeStats.mockReturnValue({ stats: null, loading: true, error: null });
    const { rerender } = render(<Dashboard />);
    expect(screen.getByText(/Cargando estadísticas.../i)).toBeInTheDocument();

    useRealtimeStats.mockReturnValue({ stats: null, loading: false, error: 'Fallo crítico' });
    rerender(<Dashboard />);
    expect(screen.getByText(/Error al cargar datos: Fallo crítico/i)).toBeInTheDocument();
  });

  test('debe permitir filtrar por dispositivo y pasar el ID al histograma', () => {
    render(<Dashboard />);
    const label = screen.getByText(/Dispositivo:/i);
    const select = label.nextElementSibling;
    
    fireEvent.change(select, { target: { value: 'dev1' } });

    expect(screen.getByText(/Histogram Chart for dev1/i)).toBeInTheDocument();
  });

  test('debe alternar la visibilidad de dispositivos inactivos en la lista', () => {
    render(<Dashboard />);
    const toggleBtn = screen.getByText(/Ocultar inactivos/i);
    
    expect(screen.getByText(/Dispositivos IoT \(3\)/i)).toBeInTheDocument();

    fireEvent.click(toggleBtn);

    // Ahora solo los activos
    expect(screen.getByText(/Dispositivos IoT \(2\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Mostrar todos/i)).toBeInTheDocument();
  });

  test('debe formatear el RSSI con un decimal en el detalle por zona', () => {
    render(<Dashboard />);
    expect(screen.getByText(/RSSI promedio: -55.5 dBm/i)).toBeInTheDocument();
  });

  test('debe mostrar el indicador de actualización automática solo en modo preset', () => {
    const { rerender } = render(<Dashboard />);
    expect(screen.getByText(/Actualización automática/i)).toBeInTheDocument();
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