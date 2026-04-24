import React, { useState } from 'react';
import { Calendar, Download, Clock, Filter } from 'lucide-react';
import api from '../services/api';

const ExportFilters = () => {
  const [filterMode, setFilterMode] = useState('preset'); // 'preset', 'custom', 'range'
  const [isExporting, setIsExporting] = useState(false);
  
  const [presetSelection, setPresetSelection] = useState('30-minutes');
  
  const [customValue, setCustomValue] = useState(5);
  const [customUnit, setCustomUnit] = useState('hours');
  
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  const [selectedZone, setSelectedZone] = useState('');
  const [selectedDevice, setSelectedDevice] = useState('');

  const presetOptions = [
    { value: 30, unit: 'minutes', label: 'Últimos 30 minutos', key: '30-minutes' },
    { value: 1, unit: 'hours', label: 'Última hora', key: '1-hours' },
    { value: 6, unit: 'hours', label: 'Últimas 6 horas', key: '6-hours' },
    { value: 24, unit: 'hours', label: 'Últimas 24 horas', key: '24-hours' },
    { value: 7, unit: 'days', label: 'Últimos 7 días', key: '7-days' },
    { value: 30, unit: 'days', label: 'Últimos 30 días', key: '30-days' },
  ];

  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      const params = new URLSearchParams();
      
      // Construir parámetros según el modo de filtro seleccionado
      if (filterMode === 'preset') {
        const preset = presetOptions.find(p => p.key === presetSelection);
        if (preset) {
          params.append(`last_${preset.unit}`, preset.value.toString());
        }
      } else if (filterMode === 'custom') {
        if (customValue > 0) {
          params.append(`last_${customUnit}`, customValue.toString());
        }
      } else if (filterMode === 'range') {
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
      }
      
      // Filtros adicionales
      if (selectedZone) params.append('zone', selectedZone);
      if (selectedDevice) params.append('device_id', selectedDevice);
      
      console.log('Export URL params:', params.toString());
      
      // Realizar la solicitud de exportación
      const response = await api.client.get(
        `/api/v1/export/detections/csv?${params.toString()}`, 
        {
          responseType: 'blob',
          headers: {
            'Accept': 'text/csv'
          }
        }
      );
      
      console.log('Response received:', {
        status: response.status,
        size: response.data.size,
        type: response.data.type
      });
      
      // Crear enlace para descargar el archivo CSV
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extraer nombre de archivo del header Content-Disposition si está presente
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'detections.csv';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      console.log('Downloading as:', filename);
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      console.log('Download initiated successfully');
      
    } catch (error) {
      console.error('Error al exportar:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      alert(`Error al descargar el archivo CSV: ${error.message}\nVerifica que haya datos disponibles en el rango seleccionado.`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-2 mb-6">
        <Download className="w-5 h-5 text-blue-600" />
        <h2 className="text-xl font-semibold">Exportar Detecciones</h2>
      </div>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tipo de Filtro
        </label>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => setFilterMode('preset')}
            className={`px-4 py-2 rounded-lg border-2 transition-colors ${
              filterMode === 'preset'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <Clock className="w-4 h-4 mx-auto mb-1" />
            <span className="text-sm">Preestablecido</span>
          </button>
          
          <button
            onClick={() => setFilterMode('custom')}
            className={`px-4 py-2 rounded-lg border-2 transition-colors ${
              filterMode === 'custom'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <Filter className="w-4 h-4 mx-auto mb-1" />
            <span className="text-sm">Personalizado</span>
          </button>
          
          <button
            onClick={() => setFilterMode('range')}
            className={`px-4 py-2 rounded-lg border-2 transition-colors ${
              filterMode === 'range'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <Calendar className="w-4 h-4 mx-auto mb-1" />
            <span className="text-sm">Rango de Fechas</span>
          </button>
        </div>
      </div>

      {filterMode === 'preset' && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Seleccionar Período
          </label>
          <select
            value={presetSelection}
            onChange={(e) => setPresetSelection(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {presetOptions.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {filterMode === 'custom' && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Últimos
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              min="1"
              max="365"
              value={customValue}
              onChange={(e) => setCustomValue(Number(e.target.value))}
              className="w-1/3 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Cantidad"
            />
            <select
              value={customUnit}
              onChange={(e) => setCustomUnit(e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="minutes">Minutos</option>
              <option value="hours">Horas</option>
              <option value="days">Días</option>
            </select>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Se exportarán las detecciones de los últimos {customValue}{' '}
            {customUnit === 'minutes' ? 'minutos' : customUnit === 'hours' ? 'horas' : 'días'}
          </p>
        </div>
      )}

      {filterMode === 'range' && (
        <div className="mb-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fecha de Inicio
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              max={endDate || undefined}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fecha de Fin
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              min={startDate || undefined}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {startDate && endDate && new Date(startDate) > new Date(endDate) && (
            <div className="p-2 bg-red-50 border border-red-200 rounded-md">
              <p className="text-xs text-red-600">
                ⚠️ La fecha de inicio debe ser anterior a la fecha de fin
              </p>
            </div>
          )}
        </div>
      )}

      <div className="mb-6 space-y-4 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-700">Filtros Adicionales (Opcional)</h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Zona
          </label>
          <select
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Todas las zonas</option>
            <option value="near">Cerca (Near)</option>
            <option value="medium">Media (Medium)</option>
            <option value="far">Lejos (Far)</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dispositivo IoT
          </label>
          <input
            type="text"
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            placeholder="ej: rpi-001"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <button
        onClick={handleExport}
        disabled={isExporting || (filterMode === 'range' && (!startDate || !endDate)) ||
          (filterMode === 'range' && startDate && endDate && new Date(startDate) > new Date(endDate))}
        className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isExporting ? (
          <>
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Exportando...
          </>
        ) : (
          <>
            <Download className="w-5 h-5" />
            Descargar CSV
          </>
        )}
      </button>

      <div className="mt-4 p-4 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>💡 Nota:</strong> El archivo CSV incluirá todas las columnas: ID, Hash del
          dispositivo, RSSI, Zona, Timestamp, Device ID, Fecha y Hora.
        </p>
      </div>
    </div>
  );
};

export default ExportFilters;