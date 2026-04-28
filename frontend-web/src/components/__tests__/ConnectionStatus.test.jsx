import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ConnectionStatus from '../ConnectionStatus';

describe('ConnectionStatus Component', () => {
  test('debe mostrar estado "Conectado" con estilos verdes cuando prop connected es true', () => {
    const { container } = render(<ConnectionStatus connected={true} />);
    
    expect(screen.getByText(/conectado/i)).toBeInTheDocument();
    
    const statusDiv = container.firstChild;
    expect(statusDiv).toHaveClass('bg-green-100');
    expect(statusDiv).toHaveClass('text-green-700');

    const icon = container.querySelector('.lucide-wifi');
    expect(icon).toBeInTheDocument();
  });

  test('debe mostrar estado "Desconectado" en rojo cuando prop connected es false', () => {
    const { container } = render(<ConnectionStatus connected={false} />);
    
    expect(screen.getByText(/desconectado/i)).toBeInTheDocument();
    
    const statusDiv = container.firstChild;
    expect(statusDiv).toHaveClass('bg-red-100');
    expect(statusDiv).toHaveClass('text-red-700');
    
    const icon = container.querySelector('.lucide-wifi-off');
    expect(icon).toBeInTheDocument();
  });
});