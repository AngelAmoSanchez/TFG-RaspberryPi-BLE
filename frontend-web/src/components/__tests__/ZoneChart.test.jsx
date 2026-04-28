import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, test, expect, vi } from 'vitest';
import ZoneChart from '../ZoneChart';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  PieChart: ({ children }) => <div>{children}</div>,
  Pie: ({ data, label }) => (
    <div>
      {data.map((entry, i) => (
        <div key={i}>
          {/* Renderizado de la etiqueta que genera Recharts */}
          {typeof label === 'function' ? label(entry) : entry.name}
        </div>
      ))}
    </div>
  ),
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => <div>Legend Rendered</div>,
}));

describe('ZoneChart Component', () => {
  test('debe mostrar mensaje "No hay datos" si el objeto data está vacío', () => {
    render(<ZoneChart data={{}} />);
    expect(screen.getByText(/no hay datos disponibles/i)).toBeInTheDocument();
  });

  test('debe transformar los datos de zonas para el gráfico', () => {
    const mockData = {
      near: { estimated_people: 5, unique_devices: 3 },
      medium: { estimated_people: 2, unique_devices: 1 }
    };
    
    render(<ZoneChart data={mockData} />);
    
    expect(screen.getByText(/Near/i)).toBeInTheDocument();
    expect(screen.getByText(/Medium/i)).toBeInTheDocument();
  });
});