import { io } from 'socket.io-client';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.connected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  /**
   * Conecta al WebSocket del backend y configura los eventos
   */
  connect() {
    if (this.socket?.connected) {
      console.log('WebSocket ya conectado');
      return;
    }

    console.log('Conectando a WebSocket:', WS_URL);

    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts
    });

    // Connection events
    this.socket.on('connect', () => {
      console.log('OK - WebSocket conectado');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.emit('connection_status', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('OK - WebSocket desconectado:', reason);
      this.connected = false;
      this.emit('connection_status', { connected: false, reason });
    });

    this.socket.on('connect_error', (error) => {
      console.error('ERROR - Error de conexión con WebSocket:', error.message);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('ERROR - Máximo de intentos de reconexión alcanzado');
        this.emit('connection_error', { error: 'Máximo de intentos de reconexión' });
      }
    });

    // Escucha eventos del backend
    this.socket.on('detection_event', (data) => {
      console.log('New detection event:', data);
      this.emit('detection_event', data);
    });

    this.socket.on('stats_update', (data) => {
      console.log('Stats update:', data);
      this.emit('stats_update', data);
    });

    // Mantener la conexión viva con pings periódicos
    setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit('ping');
      }
    }, 30000);
  }

  /**
   * Desconecta del WebSocket
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      console.log('WebSocket desconectado');
    }
  }

  /**
   * Suscribe a eventos del WebSocket
   * @param {string} event - Nombre del evento
   * @param {function} callback - Función a ejecutar cuando se reciba el evento (callback)
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * Desuscribe de eventos del WebSocket
   * @param {string} event - Nombre del evento
   * @param {function} callback - Función a ejecutar cuando se reciba el evento (callback)
   */
  off(event, callback) {
    if (!this.listeners.has(event)) return;
    
    const callbacks = this.listeners.get(event);
    const index = callbacks.indexOf(callback);
    if (index > -1) {
      callbacks.splice(index, 1);
    }
  }

  /**
   * Emite un evento a todos los oyentes
   * @param {string} event - Nombre del evento
   * @param {any} data - Datos del evento
   */
  emit(event, data) {
    if (!this.listeners.has(event)) return;
    
    this.listeners.get(event).forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${event} listener:`, error);
      }
    });
  }

  /**
   * Verifica si el WebSocket está conectado
   * @returns {boolean} - True si está conectado, false si no
   */
  isConnected() {
    return this.connected && this.socket?.connected;
  }

  /**
   * Envía un mensaje al backend a través del WebSocket
   * @param {string} event - Nombre del evento
   * @param {any} data - Datos a enviar
   */
  send(event, data) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('No se puede enviar el mensaje: WebSocket no conectado');
    }
  }
}

export default new WebSocketService();
