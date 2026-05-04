/**
 *   kind === 'rolling-minutes'  -  "Últimos N minutos" desde now(). Llama al
 *                                  endpoint /statistics/realtime con minutes.
 *   kind === 'today'            -  Desde 00:00 de hoy hasta now(). Se recalcula
 *                                  el end_time en cada fetch para tiempo real.
 *   kind === 'yesterday'        -  Desde 00:00 de ayer hasta 23:59:59 de ayer.
 */

export const TIME_PRESETS = [
  { key: 'last-1min', label: 'Último minuto', kind: 'rolling-minutes', minutes: 1 },
  { key: 'last-5min', label: 'Últimos 5 minutos', kind: 'rolling-minutes', minutes: 5 },
  { key: 'last-30min', label: 'Últimos 30 minutos', kind: 'rolling-minutes', minutes: 30 },
  { key: 'last-hour', label: 'Última hora', kind: 'rolling-minutes', minutes: 60 },
  { key: 'last-12h', label: 'Últimas 12 horas', kind: 'rolling-minutes', minutes: 720 },
  { key: 'today', label: 'Hoy', kind: 'today' },
  { key: 'yesterday', label: 'Ayer', kind: 'yesterday' },
  { key: 'last-week', label: 'Última semana', kind: 'rolling-minutes', minutes: 10080 },
  { key: 'last-month', label: 'Último mes', kind: 'rolling-minutes', minutes: 43800 }, // 30 días
  { key: 'last-quarter', label: 'Último trimestre', kind: 'rolling-minutes', minutes: 131400 }, // 90 días
  { key: 'last-year', label: 'Último año', kind: 'rolling-minutes', minutes: 525600 }, // 365 días
];

export const DEFAULT_PRESET_KEY = 'last-5min';

/**
 * Devuelve el preset por su key (o el por defecto si no se encuentra)
 */
export function getPresetByKey(key) {
  return TIME_PRESETS.find((p) => p.key === key) || null;
}

/**
 * Dado un valor en minutos, busca el preset rolling-minutes equivalente.
 */
export function getPresetByMinutes(minutes) {
  return (
    TIME_PRESETS.find((p) => p.kind === 'rolling-minutes' && p.minutes === minutes) || null
  );
}

/**
 * Formatea una fecha como string ISO local SIN zona horaria
 */
function toLocalIsoString(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  );
}

/**
 * Resuelve un preset (por key) a un objeto con instrucciones para el fetch.
 */
export function resolvePresetRequest(presetKey) {
  const preset = getPresetByKey(presetKey);
  if (!preset) return null;

  if (preset.kind === 'rolling-minutes') {
    return { type: 'minutes', minutes: preset.minutes };
  }

  if (preset.kind === 'today') {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const end = new Date(); // ahora mismo
    return {
      type: 'range',
      startDateTime: toLocalIsoString(start),
      endDateTime: toLocalIsoString(end),
    };
  }

  if (preset.kind === 'yesterday') {
    const start = new Date();
    start.setDate(start.getDate() - 1);
    start.setHours(0, 0, 0, 0);
    const end = new Date();
    end.setDate(end.getDate() - 1);
    end.setHours(23, 59, 59, 999);
    return {
      type: 'range',
      startDateTime: toLocalIsoString(start),
      endDateTime: toLocalIsoString(end),
    };
  }

  return null;
}

/**
 * Etiqueta corta para mostrar en cabeceras / descripciones.
 * Si presetKey no se reconoce, devuelve la etiqueta por defecto.
 */
export function getPresetLabel(presetKey) {
  const preset = getPresetByKey(presetKey);
  return preset ? preset.label : '';
}
