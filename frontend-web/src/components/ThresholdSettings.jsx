import React, { useState, useEffect } from 'react';
import { Settings, AlertCircle, RotateCcw } from 'lucide-react';
import api from '../services/api';

const ThresholdSettings = () => {
  const [thresholds, setThresholds] = useState({
    near_threshold: -60,
    medium_threshold: -75
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadThresholds();
  }, []);

  const loadThresholds = async () => {
    try {
      setLoading(true);
      const data = await api.getThresholds();
      setThresholds({
        near_threshold: data.near_threshold,
        medium_threshold: data.medium_threshold
      });
      setError(null);
    } catch (err) {
      console.error('Error al cargar umbrales:', err);
    } finally {
      setLoading(false);
    }
  };

  const validateThreshold = (value) => {
    const num = parseInt(value);
    if (isNaN(num)) return false;
    if (num > -1 || num < -127) return false;
    return true;
  };

  const sanitizeInput = (value) => {
    // Permitir solo: vacío, "-", o número negativo válido
    if (value === '' || value === '-') {
      return value;
    }

    // Eliminar caracteres inválidos excepto - y números
    let cleaned = value.replace(/[^0-9-]/g, '');

    // Asegurar solo un guion al inicio
    if (cleaned.startsWith('-')) {
      cleaned = '-' + cleaned.slice(1).replace(/-/g, '');
    } else {
      cleaned = cleaned.replace(/-/g, '');
    }

    // Si solo hay guion, devolver guion
    if (cleaned === '-') {
      return '-';
    }

    // Convertir a número y devolver como string
    const num = parseInt(cleaned);
    if (isNaN(num)) {
      return '';
    }

    return num.toString();
  };

  const normalizeValue = (value) => {
    // Normalizar valor al salir del input (quitar ceros a la izquierda)
    if (value === '' || value === '-') {
      return '';
    }

    const num = parseInt(value);
    if (isNaN(num)) {
      return '';
    }

    return num;
  };

  const handleInputChange = (field, rawValue) => {
    const sanitized = sanitizeInput(rawValue);
    setThresholds({ ...thresholds, [field]: sanitized });
    setError(null);
  };

  const handleBlur = async (field) => {
    // quitar ceros a la izquierda
    const normalized = normalizeValue(thresholds[field]);

    // Actualizar valor
    if (normalized !== thresholds[field]) {
      setThresholds({ ...thresholds, [field]: normalized });
    }

    // Si está vacío, no validar
    if (normalized === '' || normalized === '-') {
      setError('Valor requerido');
      return;
    }

    // Validar rango
    if (!validateThreshold(normalized)) {
      setError('Valor debe estar entre -1 y -127 dBm');
      return;
    }

    const near = field === 'near_threshold' ? normalized : thresholds.near_threshold;
    const medium = field === 'medium_threshold' ? normalized : thresholds.medium_threshold;

    // Validar que near > medium
    if (parseInt(near) <= parseInt(medium)) {
      setError('NEAR debe ser mayor que MEDIUM');
      return;
    }

    // Auto-guardar si es válido
    try {
      setSaving(true);
      setError(null);

      await api.updateThresholds(parseInt(near), parseInt(medium));

    } catch (err) {
      setError('Error al guardar');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    // Reset DIRECTO sin confirmación
    try {
      setSaving(true);
      setError(null);

      await api.resetThresholds();
      await loadThresholds(); // Recargar valores desde el backend

    } catch (err) {
      setError('Error al resetear umbrales');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 mb-1">Umbrales RSSI</p>
            <p className="text-xs text-gray-500">Cargando...</p>
          </div>
          <div className="p-3 rounded-full bg-purple-100 text-purple-600">
            <Settings className="w-6 h-6" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        {/* Texto a la izquierda */}
        <div>
          <p className="text-sm text-gray-600 mb-1">Umbrales RSSI</p>
          <p className="text-xs text-gray-500">Configuración de zonas</p>
        </div>

        {/* Botón Reset + Ícono */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-2 py-1 text-xs text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            title="Resetear a valores por defecto (-60, -75)"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>

          <div className="p-3 rounded-full bg-purple-100 text-purple-600">
            <Settings className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Inputs */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">
            NEAR
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={thresholds.near_threshold}
              onChange={(e) => handleInputChange('near_threshold', e.target.value)}
              onBlur={() => handleBlur('near_threshold')}
              disabled={saving}
              className="w-16 px-2 py-1 text-sm text-right border border-gray-300 rounded focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100"
              placeholder="-60"
            />
            <span className="text-xs text-gray-600 w-10">dBm</span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">
            MEDIUM
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={thresholds.medium_threshold}
              onChange={(e) => handleInputChange('medium_threshold', e.target.value)}
              onBlur={() => handleBlur('medium_threshold')}
              disabled={saving}
              className="w-16 px-2 py-1 text-sm text-right border border-gray-300 rounded focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100"
              placeholder="-75"
            />
            <span className="text-xs text-gray-600 w-10">dBm</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-red-800">{error}</p>
        </div>
      )}

      {saving && (
        <div className="mt-3">
          <p className="text-xs text-purple-600 animate-pulse">Guardando...</p>
        </div>
      )}
    </div>
  );
};

export default ThresholdSettings;