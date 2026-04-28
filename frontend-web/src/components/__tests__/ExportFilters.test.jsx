import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExportFilters from '../ExportFilters';
import api from '@/services/api';
import { useDevices } from '@/hooks/useDevices';

// Implementación original de los métodos del DOM
const originalCreateElement = document.createElement.bind(document);
const originalAppendChild = document.body.appendChild.bind(document.body);
const originalRemoveChild = document.body.removeChild.bind(document.body);

vi.mock('@/hooks/useDevices', () => {
  const mockHook = vi.fn(() => ({
    devices: [{ device_id: 'dev1', name: 'Sensor 1', is_active: true }],
    loading: false,
    error: null
  }));
  return { useDevices: mockHook, default: mockHook };
});

vi.mock('@/services/api', () => ({
  default: { client: { get: vi.fn() } }
}));

describe('ExportFilters Component', () => {
  const mockLink = { 
    href: '', 
    setAttribute: vi.fn(), 
    click: vi.fn(), 
    style: {},
    remove: vi.fn() 
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mocks de URL
    global.URL.createObjectURL = vi.fn(() => 'mock-url');
    global.URL.revokeObjectURL = vi.fn();
    
    // Mock de createElement
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') return mockLink;
      return originalCreateElement(tag);
    });

    // Mocks selectivos de Body para evitar interferencias con React
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
      if (node === mockLink) return node; // Sin el link falso
      return originalAppendChild(node);
    });

    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => {
      if (node === mockLink) return node;
      return originalRemoveChild(node);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('debe cambiar entre modos de filtro y mostrar los inputs correctos', () => {
    render(<ExportFilters />);
    expect(screen.getByText(/seleccionar período/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Personalizado'));
    expect(screen.getByPlaceholderText(/cantidad/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Rango de Fechas'));
    expect(screen.getByText(/fecha de inicio/i)).toBeInTheDocument();
  });

  test('debe construir parámetros correctamente en modo personalizado', async () => {
    api.client.get.mockResolvedValue({ 
      data: new Blob(['test']), 
      headers: { 'content-disposition': 'attachment; filename="test.csv"' } 
    });

    render(<ExportFilters />);
    fireEvent.click(screen.getByText('Personalizado'));
    
    fireEvent.change(screen.getByPlaceholderText(/cantidad/i), { target: { value: '10' } });
    fireEvent.change(screen.getByDisplayValue(/horas/i), { target: { value: 'days' } });

    fireEvent.click(screen.getByRole('button', { name: /descargar csv/i }));

    await waitFor(() => {
      expect(api.client.get).toHaveBeenCalledWith(
        expect.stringContaining('last_days=10'),
        expect.any(Object)
      );
    });
  });

  test('debe procesar el nombre del archivo desde headers', async () => {
    api.client.get.mockResolvedValue({
      data: new Blob(['data']),
      headers: { 'content-disposition': 'attachment; filename="reporte_detecciones.csv"' }
    });

    render(<ExportFilters />);
    fireEvent.click(screen.getByRole('button', { name: /descargar csv/i }));

    await waitFor(() => {
      expect(mockLink.setAttribute).toHaveBeenCalledWith('download', 'reporte_detecciones.csv');
      expect(mockLink.click).toHaveBeenCalled();
    });
  });

  test('debe manejar errores en bloque catch', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    api.client.get.mockRejectedValue(new Error('API Failure'));

    render(<ExportFilters />);
    fireEvent.click(screen.getByRole('button', { name: /descargar csv/i }));

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('API Failure'));
      expect(consoleSpy).toHaveBeenCalled();
    });
  });

  test('debe mostrar cargador y filtro de zona', async () => {
    api.client.get.mockImplementation(() => new Promise(res => setTimeout(() => res({ data: new Blob() }), 50)));

    render(<ExportFilters />);
    
    const zoneSelect = screen.getByText(/todas las zonas/i).closest('select');
    fireEvent.change(zoneSelect, { target: { value: 'near' } });

    fireEvent.click(screen.getByRole('button', { name: /descargar csv/i }));

    // Estado isExporting desactiva el botón
    expect(screen.getByText(/exportando/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(api.client.get).toHaveBeenCalledWith(expect.stringContaining('zone=near'), expect.any(Object));
    });
  });
});