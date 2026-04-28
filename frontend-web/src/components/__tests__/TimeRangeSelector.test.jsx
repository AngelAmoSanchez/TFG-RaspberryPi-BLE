import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TimeRangeSelector from '../TimeRangeSelector';

describe('TimeRangeSelector Component', () => {
  const mockOnChange = vi.fn();

  test('debe mostrar el label inicial basado en currentValue', () => {
    render(<TimeRangeSelector currentValue={5} onTimeRangeChange={mockOnChange} />);
    expect(screen.getByText(/5 minutos/i)).toBeInTheDocument();
  });

  test('debe abrir el dropdown al hacer click', () => {
    render(<TimeRangeSelector onTimeRangeChange={mockOnChange} />);
    // Botón principal buscado por su texto inicial (buscando solo el botón daba problemillas)
    const mainButton = screen.getByText(/minutos/i).closest('button');
    fireEvent.click(mainButton);
    
    expect(screen.getByText('Predeterminado')).toBeInTheDocument();
    expect(screen.getByText('Rango Personalizado')).toBeInTheDocument();
  });

  test('debe cambiar de preset y cerrar el dropdown (presets)', () => {
    render(<TimeRangeSelector onTimeRangeChange={mockOnChange} />);
    const mainButton = screen.getByText(/minutos/i).closest('button');
    fireEvent.click(mainButton);
    
    const option1Hour = screen.getByText('1 hora');
    fireEvent.click(option1Hour);
    
    expect(mockOnChange).toHaveBeenCalledWith({ mode: 'preset', value: 60 });
    expect(screen.queryByText('Predeterminado')).not.toBeInTheDocument();
  });

  describe('Modo Personalizado', () => {
    beforeEach(async () => {
      render(<TimeRangeSelector onTimeRangeChange={mockOnChange} />);
      const mainButton = screen.getByRole('button', { name: /minutos|hora|día/i });
      fireEvent.click(mainButton);
      
      const customTab = screen.getByText('Rango Personalizado').closest('button');
      fireEvent.click(customTab);
    });

    test('debe mostrar error si la fecha de inicio es posterior a la de fin', () => {
      // Selector de etiquetas de forma manual (JSDOM a veces se ralla y no reconoce 'datetime-local' como rol)
      const labels = [
        screen.getByText(/fecha y hora de inicio/i),
        screen.getByText(/fecha y hora de fin/i)
      ];
      
      const inputInicio = labels[0].nextElementSibling;
      const inputFin = labels[1].nextElementSibling;

      fireEvent.change(inputInicio, { target: { value: '2026-04-27T12:00' } });
      fireEvent.change(inputFin, { target: { value: '2026-04-27T10:00' } });

      expect(screen.getByText(/debe ser anterior/i)).toBeInTheDocument();
    });

    test('debe llamar a onTimeRangeChange con los datos correctos al aplicar', () => {
      const labels = [
        screen.getByText(/fecha y hora de inicio/i),
        screen.getByText(/fecha y hora de fin/i)
      ];
      
      fireEvent.change(labels[0].nextElementSibling, { target: { value: '2026-04-27T10:00' } });
      fireEvent.change(labels[1].nextElementSibling, { target: { value: '2026-04-27T12:00' } });

      const applyBtn = screen.getByRole('button', { name: /aplicar rango/i });
      fireEvent.click(applyBtn);

      expect(mockOnChange).toHaveBeenCalled();
    });
  });
});