const WS_URL = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000').replace('/socket.io', '/ws');

class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.connected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.reconnectTimer = null;
    this.pingInterval = null;
  }

  /**
   * Conecta al WebSocket del backend y configura los eventos
   */
  connect() {
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log('WebSocket ya conectado');
      return;
    }

    console.log('Conectando a WebSocket:', WS_URL);

    try {
      this.socket = new WebSocket(WS_URL);
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      this.scheduleReconnect();
      return;
    }

    this.socket.onopen = () => {
      console.log('OK - WebSocket conectado');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.emit('connection_status', { connected: true });
      this.startPing();
    };

    this.socket.onclose = (event) => {
      console.log('OK - WebSocket desconectado:', event.code, event.reason);
      this.connected = false;
      this.stopPing();
      this.emit('connection_status', { connected: false, reason: event.reason });
      if (event.code !== 1000) { // Desconxión rara o inesperada
        this.scheduleReconnect();
      }
    };

    this.socket.onerror = (error) => {
      console.error('ERROR - Error de conexión con WebSocket:', error);
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type && this.listeners.has(message.type)) {
          this.emit(message.type, message);
        }
      } catch (e) {
        console.error('ERROR - Error parseando mensaje de WebSocket:', e);
      }
    };
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('ERROR - Máximo de intentos de reconexión alcanzado');
      this.emit('connection_error', { error: 'Máximo de intentos de reconexión' });
      return;
    }
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Reconectando en ${delay}ms (intento ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  startPing() {
    this.stopPing();

    // Mantener la conexión viva con pings periódicos
    this.pingInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send('ping');
      }
    }, 30000);
  }

  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

    /**
   * Desconecta del WebSocket
   */
  disconnect() {
    this.stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
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
    return this.connected && this.socket?.readyState === WebSocket.OPEN;
  }

  /**
   * Envía un mensaje al backend a través del WebSocket
   * @param {string} event - Nombre del evento
   * @param {any} data - Datos a enviar
   */
  send(event, data) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: event, ...data }));
    } else {
      console.warn('No se puede enviar el mensaje: WebSocket no conectado');
    }
  }
}

export default new WebSocketService();
