import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { 
  getPresetByKey, 
  getPresetByMinutes, 
  resolvePresetRequest, 
  getPresetLabel,
  TIME_PRESETS,
  DEFAULT_PRESET_KEY
} from '../timePresets';

describe('timePresets logic', () => {
  
  beforeEach(() => {
    // Fijamos una fecha específica para los tests de 'today' y 'yesterday'
    // Domingo, 17 de Mayo de 2026, 11:30:00
    const mockDate = new Date(2026, 4, 17, 11, 30, 0);
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test('debe contener los presets básicos y el valor por defecto correcto', () => {
    expect(TIME_PRESETS.length).toBeGreaterThan(0);
    expect(DEFAULT_PRESET_KEY).toBe('last-5min');
  });

  test('getPresetByKey debe devolver el objeto correcto o null', () => {
    const preset = getPresetByKey('last-1min');
    expect(preset.label).toBe('Último minuto');
    expect(preset.minutes).toBe(1);

    expect(getPresetByKey('non-existent')).toBeNull();
  });

  test('getPresetByMinutes debe encontrar presets de tipo rolling-minutes', () => {
    const preset = getPresetByMinutes(60);
    expect(preset.key).toBe('last-hour');

    // No debe encontrar presets que no sean rolling-minutes aunque coincidan minutos (si los hubiera)
    expect(getPresetByMinutes(999999)).toBeNull();
  });

  test('getPresetLabel debe devolver la etiqueta o un string vacío', () => {
    expect(getPresetLabel('today')).toBe('Hoy');
    expect(getPresetLabel('invalid')).toBe('');
  });

  describe('resolvePresetRequest', () => {
    test('debe resolver presets de tipo rolling-minutes', () => {
      const result = resolvePresetRequest('last-30min');
      expect(result).toEqual({
        type: 'minutes',
        minutes: 30
      });
    });

    test('debe resolver el preset "today" con el rango horario correcto', () => {
      const result = resolvePresetRequest('today');
      
      expect(result.type).toBe('range');
      // Inicio: 2026-05-17T00:00:00 (Local)
      expect(result.startDateTime).toBe('2026-05-17T00:00:00');
      // Fin: 2026-05-17T11:30:00 (Hora fijada en el mock)
      expect(result.endDateTime).toBe('2026-05-17T11:30:00');
    });

    test('debe resolver el preset "yesterday" con el día anterior completo', () => {
      const result = resolvePresetRequest('yesterday');
      
      expect(result.type).toBe('range');
      // Inicio: 2026-05-16T00:00:00
      expect(result.startDateTime).toBe('2026-05-16T00:00:00');
      // Fin: 2026-05-16T23:59:59
      expect(result.endDateTime).toBe('2026-05-16T23:59:59');
    });

    test('debe devolver null para claves inválidas', () => {
      expect(resolvePresetRequest('unknown-key')).toBeNull();
    });
  });

  test('toLocalIsoString (vía resolvePresetRequest) debe formatear correctamente con pads de cero', () => {
    const singleDigitDate = new Date(2026, 0, 5, 8, 5, 9);
    vi.setSystemTime(singleDigitDate);
    
    const result = resolvePresetRequest('today');
    expect(result.startDateTime).toBe('2026-01-05T00:00:00');
    expect(result.endDateTime).toBe('2026-01-05T08:05:09');
  });
});