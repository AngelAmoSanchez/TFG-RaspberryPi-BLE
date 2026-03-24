import React, { useState } from 'react';
import { useExport } from '../../controllers/useExport';

function ExportButton({ startDate, endDate }) {
  const { exportCSV, exporting, error } = useExport();
  const [message, setMessage] = useState('');

  const handleExport = async () => {
    const success = await exportCSV(startDate, endDate);

    if (success) {
      setMessage('OK - Archivo descargado correctamente');
      setTimeout(() => setMessage(''), 3000);
    } else {
      setMessage(`ERROR - Error: ${error}`);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <button
        onClick={handleExport}
        disabled={exporting}
        style={{
          padding: '10px 20px',
          background: exporting ? '#9C9C9C' : '#009CDD',
          color: '#fff',
          border: 'none',
          borderRadius: '6px',
          cursor: exporting ? 'not-allowed' : 'pointer',
          fontSize: '14px',
          fontWeight: '500'
        }}
      >
        {exporting ? 'Exportando...' : 'Exportar CSV'}
      </button>
      {message && (
        <span style={{ color: message.includes('OK') ? '#6d8d70' : '#FF474C', fontSize: '14px' }}>
          {message}
        </span>
      )}
    </div>
  );
}

export default ExportButton;
