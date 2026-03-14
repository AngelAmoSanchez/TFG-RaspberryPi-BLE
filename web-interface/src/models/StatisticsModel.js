
// Modelo de datos para estadísticas

/**
 * Agrupa las estadísticas por cada zona
 * @param {Array} statistics - Estadísticas del backend
*/
export function groupByZone(statistics) {
  const grouped = { near: [], medium: [], far: [] };
  statistics.forEach(stat => {
    if (grouped[stat.zone]) grouped[stat.zone].push(stat);
  });
  return grouped;
}

/**
 * Calcula dispositivos y personas totales por cada zona
 * @param {Array} statistics 
*/
export function calculateZoneTotals(statistics) {
  const totals = { near: 0, medium: 0, far: 0 };
  statistics.forEach(stat => {
    totals[stat.zone] = (totals[stat.zone] || 0) + stat.estimated_people;
  });
  return totals;
}

/**
 * Formatea datos para poder mostrarlos en gráficos de Recharts
 * @param {Array} statistics 
*/
export function formatForChart(statistics) {
  return statistics.map(stat => ({
    time: new Date(stat.start_time).toLocaleTimeString('es-ES', { 
      hour: '2-digit', minute: '2-digit' 
    }),
    timestamp: stat.start_time,
    zone: stat.zone,
    people: stat.estimated_people,
    devices: stat.unique_devices,
    permanence: stat.avg_permanence_minutes
  }));
}

/**
 * Obtiene el nombre de la zona asignada
*/
export function getZoneLabel(zone) {
  const labels = {
    near: 'Zona Cercana (< 2m)',
    medium: 'Zona Media (2-5m)',
    far: 'Zona Lejana (> 5m)'
  };
  return labels[zone] || zone;
}

/**
 * Obtiene el color asociado a cada zona (para los gráficos)
*/
export function getZoneColor(zone) {
  const colors = {
    near: '#FF474C',
    medium: '#FFA800',
    far: '#009CDD'
  };
  return colors[zone] || '#9C9C9C';
}
