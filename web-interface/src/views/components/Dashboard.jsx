import React, { useState } from 'react';
import { useHourlyStatistics, useCurrentSummary } from '../../controllers/useStatistics';
import ZoneChart from './ZoneChart';
import ExportButton from './ExportButton';

function Dashboard() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const { data, loading, error, refresh } = useHourlyStatistics(selectedDate);
  const { summary } = useCurrentSummary();

  if (loading) return <div style={{ textAlign: 'center', padding: '100px' }}>Cargando datos...</div>;
  if (error) return <div style={{ textAlign: 'center', padding: '100px', color: '#ef4444' }}>Error: {error}</div>;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <header style={{ textAlign: 'center', marginBottom: '30px', paddingBottom: '20px', borderBottom: '2px solid #dcdee2' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', margin: '0 0 10px 0' }}>
          Sistema de Conteo de Personas - Bluetooth BLE
        </h1>
        <p style={{ fontSize: '16px', color: '#666', margin: 0 }}>
          Estimación de afluencia mediante detección BLE
        </p>
      </header>

      {summary && summary.length > 0 && (
        <div style={{ marginBottom: '30px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '15px' }}>
            Estado en tiempo real (Última hora)
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            {summary.map((zone) => (
              <div key={zone.zone} style={{
                background: 'linear-gradient(135deg, #009CDD 0%, #824eb6 100%)',
                color: '#fff', padding: '20px', borderRadius: '12px', textAlign: 'center'
              }}>
                <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '10px' }}>
                  {zone.zone.toUpperCase()}
                </div>
                <div style={{ fontSize: '36px', fontWeight: '700', marginBottom: '5px' }}>
                  {zone.estimated_people}
                </div>
                <div style={{ fontSize: '14px' }}>personas estimadas</div>
                <div style={{ fontSize: '12px', marginTop: '5px', opacity: 0.8 }}>
                  {zone.unique_devices} dispositivos
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '20px', padding: '15px', background: '#dcdee2', borderRadius: '8px'
      }}>
        <label style={{ fontSize: '14px', fontWeight: '500' }}>
          Seleccionar fecha:
          <input
            type="date"
            value={selectedDate.toISOString().split('T')[0]}
            onChange={(e) => setSelectedDate(new Date(e.target.value))}
            style={{ marginLeft: '10px', padding: '8px 12px', border: '1px solid #dcdee2', borderRadius: '6px' }}
          />
        </label>
         {<ExportButton startDate={selectedDate} endDate={selectedDate} />} 
      </div>

      {data && <ZoneChart data={data.totals} title="Distribución de dispositivos por zona" />}

      <footer style={{
        marginTop: '40px', padding: '20px', background: '#ffffff', borderRadius: '8px',
        fontSize: '14px', color: '#666', textAlign: 'center'
      }}>
        <p> Las estimaciones están realizadas con los datos de los dispositivos Bluetooth detectados. </p>
        <p> - </p> 
        <p> No se almacenan datos personales identificables (RGPD).</p>
      </footer>
    </div>
  );
}

export default Dashboard;
