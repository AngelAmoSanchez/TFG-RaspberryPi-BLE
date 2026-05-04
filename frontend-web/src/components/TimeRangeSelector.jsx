import React, { useState, useEffect } from 'react';
import { Clock, Calendar, ChevronDown } from 'lucide-react';
import { TIME_PRESETS, DEFAULT_PRESET_KEY, getPresetByKey, getPresetByMinutes } from './timePresets';

const TimeRangeSelector = ({ onTimeRangeChange, currentPresetKey, currentValue = 5 }) => {

  const resolvedKey =
    currentPresetKey ||
    getPresetByMinutes(currentValue)?.key ||
    DEFAULT_PRESET_KEY;

  const [mode, setMode] = useState('preset'); // 'preset' o 'custom'
  const [showDropdown, setShowDropdown] = useState(false);
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Sincroniza el modo si el se cambia entre preset/custom en el dashboard
  useEffect(() => {
    if (currentPresetKey) setMode('preset');
  }, [currentPresetKey]);

  const formatDateForDisplay = (datetimeStr) => {
    if (!datetimeStr) return '';
    const date = new Date(datetimeStr);
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getCurrentLabel = () => {
    if (mode === 'custom' && customStart && customEnd) {
      return `${formatDateForDisplay(customStart)} - ${formatDateForDisplay(customEnd)}`;
    }
    const preset = getPresetByKey(resolvedKey);
    return preset ? preset.label : 'Últimos 5 minutos';
  };

  const handlePresetChange = (preset) => {
    setMode('preset');
    setShowDropdown(false);

    // Payload de cambio entre presets
    const payload = { mode: 'preset', presetKey: preset.key };
    if (preset.kind === 'rolling-minutes') {
      payload.value = preset.minutes;
    }
    onTimeRangeChange(payload);
  };

  const handleCustomApply = () => {
    if (customStart && customEnd) {
      setMode('custom');
      setShowDropdown(false);

      const startDate = customStart.split('T')[0];
      const endDate = customEnd.split('T')[0];

      onTimeRangeChange({
        mode: 'custom',
        startDate,
        endDate,
        startDateTime: customStart,
        endDateTime: customEnd
      });
    }
  };

  const handleModeSwitch = (newMode) => {
    setMode(newMode);
    if (newMode === 'preset') {
      const preset = getPresetByKey(resolvedKey);
      if (preset) {
        const payload = { mode: 'preset', presetKey: preset.key };
        if (preset.kind === 'rolling-minutes') payload.value = preset.minutes;
        onTimeRangeChange(payload);
      }
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[200px]"
      >
        <Clock className="w-4 h-4 text-gray-600 flex-shrink-0" />
        <span className="text-sm font-medium text-gray-700 truncate">
          {getCurrentLabel()}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${showDropdown ? 'rotate-180' : ''}`} />
      </button>

      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />

          <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => handleModeSwitch('preset')}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${mode === 'preset'
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <Clock className="w-4 h-4" />
                  Predeterminado
                </div>
              </button>

              <button
                onClick={() => handleModeSwitch('custom')}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${mode === 'custom'
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Rango Personalizado
                </div>
              </button>
            </div>

            {mode === 'preset' && (
              <div className="p-2 max-h-80 overflow-y-auto">
                {TIME_PRESETS.map((option) => (
                  <button
                    key={option.key}
                    onClick={() => handlePresetChange(option)}
                    className={`w-full text-left px-4 py-2.5 rounded-md text-sm transition-colors ${resolvedKey === option.key
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                      }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}

            {mode === 'custom' && (
              <div className="p-4 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Fecha y Hora de Inicio
                  </label>
                  <input
                    type="datetime-local"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    max={customEnd || undefined}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Fecha y Hora de Fin
                  </label>
                  <input
                    type="datetime-local"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    min={customStart || undefined}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>


                {customStart && customEnd && new Date(customStart) >= new Date(customEnd) && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-xs text-red-600">
                      La fecha de inicio debe ser anterior a la fecha de fin
                    </p>
                  </div>
                )}

                <button
                  onClick={handleCustomApply}
                  disabled={!customStart || !customEnd || new Date(customStart) >= new Date(customEnd)}
                  className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  Aplicar Rango
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default TimeRangeSelector;