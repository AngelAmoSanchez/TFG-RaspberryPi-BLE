import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import websocketService from '../websocket';

// Variable para capturar la última instancia creada
let lastCreatedSocket = null;

// Mock global del objeto WebSocket nativo del navegador
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.send = vi.fn();
    this.close = vi.fn();

    lastCreatedSocket = this;
    websocketService.socket = this;
    
    setTimeout(() => {
      if (this.onopen) {
        this.readyState = 1; // OPEN
        this.onopen();
      }
    }, 0);
  }
}

// Inyectar el mock en el entorno global de Vitest
global.WebSocket = MockWebSocket;
global.WebSocket.OPEN = 1;

describe('WebSocketService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    websocketService.disconnect();
    websocketService.listeners = new Map();
    // Resetear contadores de reconexión para tests limpios
    websocketService.reconnectAttempts = 0;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('connect() no debe duplicar la conexión si ya está conectado', () => {
    websocketService.connect();
    // Forzamos el estado OPEN para el mock
    websocketService.socket.readyState = WebSocket.OPEN;
    
    const initialSocket = websocketService.socket;
    websocketService.connect();
    
    expect(websocketService.socket).toBe(initialSocket);
  });

  it('debe configurar los handlers nativos al conectar', () => {
    websocketService.connect();
    
    expect(websocketService.socket.onopen).toBeTypeOf('function');
    expect(websocketService.socket.onmessage).toBeTypeOf('function');
    expect(websocketService.socket.onclose).toBeTypeOf('function');
  });

  it('el sistema de eventos on/emit debe funcionar internamente', () => {
    const callback = vi.fn();
    websocketService.on('custom_event', callback);
    
    websocketService.emit('custom_event', { foo: 'bar' });
    
    expect(callback).toHaveBeenCalledWith({ foo: 'bar' });
  });

  it('off() debe eliminar correctamente un suscriptor', () => {
    const callback = vi.fn();
    websocketService.on('test', callback);
    websocketService.off('test', callback);
    
    websocketService.emit('test', {});
    
    expect(callback).not.toHaveBeenCalled();
  });

  it('debe enviar pings cada 30 segundos si está conectado', () => {
    websocketService.connect();
    // Simular que el socket se abre
    websocketService.socket.readyState = WebSocket.OPEN;
    websocketService.socket.onopen();

    // El código real usa un intervalo de 15000ms
    vi.advanceTimersByTime(15000);
    
    expect(websocketService.socket.send).toHaveBeenCalledWith('ping');
  });

  it('send() debe advertir si el socket no está conectado', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    
    // Socket no conectado (readyState !== OPEN)
    websocketService.send('test', { data: 1 });
    
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('no conectado'));
  });

  it('send() debe enviar JSON stringify si está conectado', () => {
    websocketService.connect();
    websocketService.socket.readyState = WebSocket.OPEN;

    websocketService.send('test_event', { value: 123 });
    
    expect(websocketService.socket.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'test_event', value: 123 })
    );
  });

  it('disconnect() debe limpiar el estado y cerrar el socket', () => {
    websocketService.connect();
    const socketSpy = websocketService.socket;
    websocketService.connected = true;

    websocketService.disconnect();

    expect(socketSpy.close).toHaveBeenCalledWith(1000, 'Client disconnect');
    expect(websocketService.socket).toBeNull();
    expect(websocketService.connected).toBe(false);
  });

  it('isConnected() debe verificar la propiedad connected y el readyState', () => {
    websocketService.connect();
    
    // Caso 1: Marcado como conectado y socket en OPEN
    websocketService.connected = true;
    websocketService.socket.readyState = WebSocket.OPEN;
    expect(websocketService.isConnected()).toBe(true);

    // Caso 2: Socket cerrado
    websocketService.socket.readyState = 0; // CONNECTING
    expect(websocketService.isConnected()).toBe(false);
  });

  it('debe reconectar automáticamente si el socket se cierra de forma inesperada', () => {
    websocketService.connect();
    const socket = lastCreatedSocket;
    const scheduleSpy = vi.spyOn(websocketService, 'scheduleReconnect');
    
    socket.onclose({ code: 1006, reason: 'Abnormal' });

    expect(websocketService.connected).toBe(false);
    expect(scheduleSpy).toHaveBeenCalled();
  });

  it('debe reconectar automáticamente si el socket se cierra de forma inesperada', () => {
    websocketService.connect();
    const socket = lastCreatedSocket;
    const scheduleSpy = vi.spyOn(websocketService, 'scheduleReconnect');
    

    socket.onclose({ code: 1006, reason: 'Abnormal' });

    expect(websocketService.connected).toBe(false);
    expect(scheduleSpy).toHaveBeenCalled();
  });

  it('debe implementar backoff exponencial en los intentos de reconexión', () => {
    const logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    websocketService.reconnectAttempts = 1; 
    
    websocketService.scheduleReconnect();

    expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Reconectando en 2000ms'));
    expect(websocketService.reconnectAttempts).toBe(2);
  });

  it('debe capturar errores dentro de los callbacks de los listeners', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    websocketService.on('test_event', () => { throw new Error('Fail'); });
    
    websocketService.emit('test_event', {});
    
    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('Error in test_event listener:'), expect.any(Error));
  });
});