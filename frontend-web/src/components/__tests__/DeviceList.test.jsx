import React from 'react';
import { render, screen } from '@testing-library/react';
import DeviceList from '../DeviceList';

const mockDevices = [
  { device_id: 'DEV01', name: 'Sensor 1', location: 'Entrada', is_active: true, last_seen: '2023-10-01T10:00:00' },
  { device_id: 'DEV02', name: '', location: '', is_active: false, last_seen: null }
];

describe('DeviceList Component', () => {
  test('debe mostrar mensaje de carga cuando está cargando (loading)', () => {
    render(<DeviceList devices={[]} loading={true} />);
    expect(screen.getByText(/cargando dispositivos/i)).toBeInTheDocument();
  });

  test('debe mostrar mensaje de lista vacía si no hay dispositivos', () => {
    render(<DeviceList devices={[]} loading={false} />);
    expect(screen.getByText(/no hay dispositivos registrados/i)).toBeInTheDocument();
  });

  test('debe renderizar la tabla con los datos de los dispositivos', () => {
    render(<DeviceList devices={mockDevices} loading={false} />);
    
    // Verifica nombres o IDs
    expect(screen.getByText('Sensor 1')).toBeInTheDocument();
    expect(screen.getByText('DEV02')).toBeInTheDocument();
    
    // Verifica ubicación
    expect(screen.getByText('Entrada')).toBeInTheDocument();
    expect(screen.getByText('No especificado')).toBeInTheDocument();
    
    // Verifica que haya iconos de estado
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3);
  });

  test('debe mostrar "Nunca" si last_seen es null', () => {
    render(<DeviceList devices={[mockDevices[1]]} loading={false} />);
    expect(screen.getByText('Nunca')).toBeInTheDocument();
  });
});