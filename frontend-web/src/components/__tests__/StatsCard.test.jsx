import React from 'react';
import { render, screen } from '@testing-library/react';
import StatsCard from '../StatsCard';

describe('StatsCard Component', () => {
  const defaultProps = {
    title: 'Total Detecciones',
    value: 150,
    icon: <span data-testid="icon">Icon</span>
  };

  test('debe renderizar título, valor e icono correctamente', () => {
    render(<StatsCard {...defaultProps} />);
    expect(screen.getByText('Total Detecciones')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  test('debe renderizar el subtítulo solo si se proporciona', () => {
    const { rerender } = render(<StatsCard {...defaultProps} />);
    expect(screen.queryByText('Mi subtítulo')).not.toBeInTheDocument();

    rerender(<StatsCard {...defaultProps} subtitle="Mi subtítulo" />);
    expect(screen.getByText('Mi subtítulo')).toBeInTheDocument();
  });

  test('debe aplicar la clase de color correcta según la prop color', () => {
    render(<StatsCard {...defaultProps} color="green" />);
    const iconContainer = screen.getByTestId('icon').parentElement;
    expect(iconContainer).toHaveClass('bg-green-100');
  });
});