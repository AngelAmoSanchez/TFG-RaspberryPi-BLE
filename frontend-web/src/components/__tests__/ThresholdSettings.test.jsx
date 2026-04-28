import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ThresholdSettings from '../ThresholdSettings';
import api from '../../services/api';

// Mock del servicio API
vi.mock('../../services/api');

describe('ThresholdSettings Component', () => {
  const mockThresholds = { near_threshold: -60, medium_threshold: -75 };

  beforeEach(() => {
    api.getThresholds.mockResolvedValue(mockThresholds);
  });

  test('debe cargar y mostrar los umbrales iniciales', async () => {
    render(<ThresholdSettings />);
    await waitFor(() => {
      expect(screen.getByDisplayValue('-60')).toBeInTheDocument();
      expect(screen.getByDisplayValue('-75')).toBeInTheDocument();
    });
  });

  test('debe limpiar los valores de entrada (no permitir letras)', async () => {
    render(<ThresholdSettings />);
    await waitFor(() => screen.getByDisplayValue('-60'));
    
    const inputNear = screen.getByDisplayValue('-60');
    fireEvent.change(inputNear, { target: { value: '-60abc' } });
    
    expect(inputNear.value).toBe('-60');
  });

  test('debe mostrar error si NEAR es menor o igual a MEDIUM', async () => {
    render(<ThresholdSettings />);
    await waitFor(() => screen.getByDisplayValue('-60'));

    const inputNear = screen.getByDisplayValue('-60');

    fireEvent.change(inputNear, { target: { value: '-80' } });
    fireEvent.blur(inputNear);

    expect(screen.getByText(/NEAR debe ser mayor que MEDIUM/i)).toBeInTheDocument();
  });

  test('debe llamar a resetThresholds al pulsar reset', async () => {
    api.resetThresholds.mockResolvedValue({ success: true });
    api.getThresholds.mockResolvedValue({ near_threshold: -60, medium_threshold: -75 });
    
    render(<ThresholdSettings />);
    
    // Añadido para esperar a qyue termine de cargar la página antes de buscar el botón
    const resetBtn = await screen.findByTitle(/resetear a valores por defecto/i);
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(api.resetThresholds).toHaveBeenCalled();
    });
  });

  test('debe manejar errores al cargar y resetear umbrales', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    api.getThresholds.mockRejectedValueOnce(new Error('Fail Load'));
    api.resetThresholds.mockRejectedValueOnce(new Error('Fail Reset'));

    render(<ThresholdSettings />);
    
    // Error en carga inicial
    await waitFor(() => expect(consoleSpy).toHaveBeenCalledWith('Error al cargar umbrales:', expect.any(Error)));

    // Error en reset
    api.getThresholds.mockResolvedValue(mockThresholds);
    render(<ThresholdSettings />);
    const resetBtn = await screen.findByTitle(/resetear a valores por defecto/i);
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(screen.getByText(/Error al resetear umbrales/i)).toBeInTheDocument();
    });
    consoleSpy.mockRestore();
  });

  test('debe manejar entradas parciales como "-" o vacío en sanitizeInput', async () => {
    render(<ThresholdSettings />);
    const inputNear = await screen.findByDisplayValue('-60');

    // Permite cadena vacía
    fireEvent.change(inputNear, { target: { value: '' } });
    expect(inputNear.value).toBe('');

    // Permite solo un guion negativo
    fireEvent.change(inputNear, { target: { value: '-' } });
    expect(inputNear.value).toBe('-');

    // Convierte las entradas inválidas a vacío
    fireEvent.change(inputNear, { target: { value: 'abc' } });
    expect(inputNear.value).toBe('');
  });

  test('debe normalizar valores vacíos o inválidos al perder el foco (blur)', async () => {
    render(<ThresholdSettings />);
    const inputNear = await screen.findByDisplayValue('-60');

    // Valor pedido si se deja vacío o solo con "-"
    fireEvent.change(inputNear, { target: { value: '-' } });
    fireEvent.blur(inputNear);
    
    await waitFor(() => {
      expect(screen.getByText(/Valor requerido/i)).toBeInTheDocument();
    });
  });

  test('debe validar el rango permitido de dBm (-1 a -127)', async () => {
    render(<ThresholdSettings />);
    const inputNear = await screen.findByDisplayValue('-60');

    // Valor fuera de rango
    fireEvent.change(inputNear, { target: { value: '-130' } });
    fireEvent.blur(inputNear);

    expect(screen.getByText(/Valor debe estar entre -1 y -127 dBm/i)).toBeInTheDocument();
  });

  test('debe llamar a updateThresholds en blur y manejar error de guardado', async () => {
    api.updateThresholds.mockRejectedValueOnce(new Error('Save Fail'));
    render(<ThresholdSettings />);
    
    const inputNear = await screen.findByDisplayValue('-60');
    fireEvent.change(inputNear, { target: { value: '-55' } });
    fireEvent.blur(inputNear);

    // Estado saving
    expect(screen.getByText(/Guardando.../i)).toBeInTheDocument();

    // Error al guardar
    await waitFor(() => {
      expect(screen.getByText(/Error al guardar/i)).toBeInTheDocument();
      expect(api.updateThresholds).toHaveBeenCalledWith(-55, -75);
    });
  });
});