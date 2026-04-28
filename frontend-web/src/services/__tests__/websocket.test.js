import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { io } from 'socket.io-client';
import websocketService from '../websocket';

// Mock de socket.io-client
vi.mock('socket.io-client', () => {
  const mSocket = {
    on: vi.fn(),
    emit: vi.fn(),
    disconnect: vi.fn(),
    connected: false,
  };
  return { io: vi.fn(() => mSocket) };
});

describe('WebSocketService', () => {
  let mockSocket;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockSocket = io();
    websocketService.socket = null;
    websocketService.listeners = new Map();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('connect() no debe duplicar la conexión si ya está conectado', () => {
    mockSocket.connected = true;
    websocketService.socket = mockSocket;
    
    websocketService.connect();
    
    expect(io).not.toHaveBeenCalledTimes(2);
  });

  it('debe registrar oyentes internos al conectar (connect, disconnect, etc)', () => {
    websocketService.connect();
    
    expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('stats_update', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('detection_event', expect.any(Function));
  });

  it('el sistema de eventos on/emit debe funcionar independientemente del socket', () => {
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
    mockSocket.connected = true;
    websocketService.connect();

    vi.advanceTimersByTime(30000);
    
    expect(mockSocket.emit).toHaveBeenCalledWith('ping');
  });

  it('send() debe advertir si el socket no está conectado', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    mockSocket.connected = false;
    websocketService.socket = mockSocket;

    websocketService.send('test', {});
    
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('no conectado'));
  });

  it('disconnect() debe limpiar el estado correctamente', () => {
    websocketService.socket = mockSocket;
    websocketService.connected = true;

    websocketService.disconnect();

    expect(mockSocket.disconnect).toHaveBeenCalled();
    expect(websocketService.socket).toBeNull();
    expect(websocketService.connected).toBe(false);
  });

  it('isConnected() debe verificar ambas condiciones', () => {
    websocketService.connected = true;
    mockSocket.connected = true;
    websocketService.socket = mockSocket;
    expect(websocketService.isConnected()).toBe(true);

    mockSocket.connected = false;
    expect(websocketService.isConnected()).toBe(false);
  });
});