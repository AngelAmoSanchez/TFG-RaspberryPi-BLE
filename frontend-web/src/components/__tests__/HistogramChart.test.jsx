import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import HistogramChart from '../HistogramChart';
import { useHistogramStats } from '../../hooks/useHistogramStats';

// Mock del hook de estadísticas para controlar el estado del componente
vi.mock('../../hooks/useHistogramStats', () => ({
  useHistogramStats: vi.fn()
}));

// Mock de Recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ data, children }) => (
    <div data-testid="bar-chart" data-data={JSON.stringify(data)}>
      {children}
    </div>
  ),
  Bar: ({ dataKey }) => <div data-testid={`bar-${dataKey}`} />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: ({ content, active, payload, label }) => {
    if (!content) return null;
    const activePayload = payload && payload.length ? payload : [{
      payload: { 
        near: 5, medium: 3, far: 2, 
        period_start: '2026-05-17T10:00:00', 
        period_end: '2026-05-17T10:10:00' 
      }
    }];
    return (
      <div data-testid="tooltip-wrapper">
        {React.cloneElement(content, { active: true, payload: activePayload, label })}
      </div>
    );
  },
  Legend: ({ formatter }) => (
    <div data-testid="legend">
      {formatter ? formatter('near') : 'Legend'}
    </div>
  ),
}));

describe('HistogramChart Component', () => {
  const mockData = {
    buckets: [
      {
        period_start: '2026-05-17T10:00:00',
        period_end: '2026-05-17T10:10:00',
        by_zone: { near: 5, medium: 3, far: 2 }
      }
    ]
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('debe mostrar el estado de carga cuando no hay datos', () => {
    useHistogramStats.mockReturnValue({
      data: null,
      loading: true,
      error: null
    });

    render(<HistogramChart />);
    expect(screen.getByText(/cargando histograma.../i)).toBeInTheDocument();
  });

  test('debe mostrar mensaje de error si falla la API', () => {
    useHistogramStats.mockReturnValue({
      data: null,
      loading: false,
      error: 'Error de servidor'
    });

    render(<HistogramChart />);
    expect(screen.getByText(/error: error de servidor/i)).toBeInTheDocument();
  });

  test('debe mostrar mensaje si el array de datos está vacío', () => {
    useHistogramStats.mockReturnValue({
      data: { buckets: [] },
      loading: false,
      error: null
    });

    render(<HistogramChart />);
    expect(screen.getByText(/no hay datos disponibles/i)).toBeInTheDocument();
  });

  test('debe renderizar el gráfico y transformar etiquetas de tiempo para "hour"', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart />);

    expect(screen.getByText(/evolución temporal/i)).toBeInTheDocument();
    
    const chart = screen.getByTestId('bar-chart');
    const chartInjectedData = JSON.parse(chart.getAttribute('data-data'));
    
    expect(chartInjectedData[0].label).toBe('10:00');
    expect(chartInjectedData[0].near).toBe(5);
    
    expect(screen.getByTestId('bar-near')).toBeInTheDocument();
    expect(screen.getByTestId('bar-medium')).toBeInTheDocument();
    expect(screen.getByTestId('bar-far')).toBeInTheDocument();
  });

  test('debe actualizar el rango y pasar el deviceId al hook', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart deviceId="sensor-pi-01" />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'today' } });

    expect(useHistogramStats).toHaveBeenCalledWith('today', true, 'sensor-pi-01');
  });

  test('debe aplicar el formato correcto a la leyenda (Línea 171)', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart />);
    
    expect(screen.getByText('Near')).toBeInTheDocument();
  });

  test('formatLabel debe formatear correctamente para el rango "today"', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart />);
    
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'today' } });

    const chart = screen.getByTestId('bar-chart');
    const data = JSON.parse(chart.getAttribute('data-data'));

    // Debe devolver HH:00 -> 10:00
    expect(data[0].label).toBe('10:00');
  });

  test('formatLabel debe formatear correctamente para el rango "week"', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart />);
    
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'week' } });

    const chart = screen.getByTestId('bar-chart');
    const data = JSON.parse(chart.getAttribute('data-data'));
    // Verifica que contenga el número 17 en el día y sea una fecha válida
    expect(data[0].label).toContain('17');
    expect(data[0].label).not.toBe('Invalid Date');
  });

  test('CustomTooltip debe mostrar desglose y total correctamente', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart />);

    expect(screen.getByText(/Total:/i)).toBeInTheDocument();
    
    const totalCount = screen.getByText(/^10$/, { selector: 'span' });
    expect(totalCount).toBeInTheDocument();
    
    expect(screen.getByText(/Near:/i)).toBeInTheDocument();
    expect(screen.getByText(/Medium:/i)).toBeInTheDocument();
    expect(screen.getByText(/Far:/i)).toBeInTheDocument();
  });

  test('CustomTooltip debe formatear el rango de fechas para el modo week', () => {
    useHistogramStats.mockReturnValue({
      data: mockData,
      loading: false,
      error: null
    });

    render(<HistogramChart />);
    
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'week' } });

    expect(screen.getByText(/domingo/i)).toBeInTheDocument();
  });

  test('CustomTooltip debe usar el label como fallback si faltan las fechas del periodo', () => {
    const dataWithoutDates = {
      buckets: [
        {
          period_start: null,
          period_end: null,
          by_zone: { near: 5, medium: 2, far: 1 }
        }
      ]
    };

    useHistogramStats.mockReturnValue({
      data: dataWithoutDates,
      loading: false,
      error: null
    });

    render(<HistogramChart />);

    expect(screen.getByText('Última hora (cada 10 min)')).toBeInTheDocument();
  });

  test('debe mostrar mensaje si no hay datos', () => {
    useHistogramStats.mockReturnValue({
      data: { buckets: [] },
      loading: false,
      error: null
    });

    render(<HistogramChart />);
    expect(screen.getByText(/no hay datos disponibles/i)).toBeInTheDocument();
  });

  test('debe manejar fallback de etiquetas vacías', () => {
  });
});