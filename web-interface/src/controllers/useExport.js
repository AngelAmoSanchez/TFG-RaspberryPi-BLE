import { useState } from 'react';
import { format } from 'date-fns';
import ApiClient from '../models/ApiClient';

export function useExport() {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  const exportCSV = async (startDate, endDate) => {
    try {
      setExporting(true);
      setError(null);

      const startStr = format(startDate, 'yyyy-MM-dd');
      const endStr = format(endDate, 'yyyy-MM-dd');

      const blob = await ApiClient.exportCSV(startStr, endStr);

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `detections_${startStr}_${endStr}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return true;
    } catch (err) {
      setError(err.message);
      console.error('ERROR - Error exportando CSV:', err);
      return false;
    } finally {
      setExporting(false);
    }
  };

  return { exportCSV, exporting, error };
}
