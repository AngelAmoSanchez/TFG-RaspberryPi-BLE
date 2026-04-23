import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' }
    });

    // Pide token de autenticación en cada solicitud
    this.client.interceptors.request.use(
      config => {
        const token = localStorage.getItem('api_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      error => Promise.reject(error)
    );

    // Interceptor para manejo global de errores
    this.client.interceptors.response.use(
      response => response,
      error => {
        console.error('ERROR EN API:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // ============= DETECTIONS =============

  /**
   * Obtiene las detecciones más recientes
   * @param {number} limit - Número máximo de detecciones a obtener
   * @param {string} zone - Filtrar por zona (opcional)
   */
  async getRecentDetections(limit = 100, zone = null) {
    const params = { limit };
    if (zone) params.zone = zone;
    
    const response = await this.client.get('/api/v1/detections/recent', { params });
    return response.data;
  }

  /**
   * Obtiene el recuento de detecciones para un rango de tiempo
   * @param {number} hours - Horas para retroceder
   * @param {string} zone - Filtrar por zona (opcional)
   */
  async getDetectionCount(hours = 24, zone = null) {
    const params = { hours };
    if (zone) params.zone = zone;
    
    const response = await this.client.get('/api/v1/detections/count', { params });
    return response.data;
  }

  // ============= STATISTICS =============

  /**
   * Obtiene estadísticas en tiempo real (últimos N minutos)
   * @param {number} minutes - Minutos para retroceder
   * @returns {object} - Estadísticas agrupadas por zona
   */
  async getRealtimeStats(minutes = 5) {
    const response = await this.client.get('/api/v1/statistics/realtime', {
      params: { minutes }
    });
    return response.data;
  }

  /**
   * Obtiene estadísticas horarias para una fecha específica
   * @param {string} date - Fecha en formato YYYY-MM-DD
   */
  async getHourlyStats(date) {
    const response = await this.client.get('/api/v1/statistics/hourly', {
      params: { date }
    });
    return response.data;
  }

  /**
   * Obtiene estadísticas diarias para un rango de fechas
   * @param {string} startDate - Fecha de inicio en formato YYYY-MM-DD
   * @param {string} endDate - Fecha de finalización en formato YYYY-MM-DD
   */
  async getDailyStats(startDate, endDate) {
    const response = await this.client.get('/api/v1/statistics/daily', {
      params: { start_date: startDate, end_date: endDate }
    });
    return response.data;
  }

  /**
   * Obtiene la distribución de zonas
   * @param {number} hours - Horas para retroceder (por defecto 24 horas)
   * @returns {object} - Distribución de personas por zona
   */
  async getZoneDistribution(hours = 24) {
    const response = await this.client.get('/api/v1/statistics/distribution', {
      params: { hours }
    });
    return response.data;
  }

  // ============= DEVICES =============

  /**
   * Obtiene todos los dispositivos IoT registrados
   * @param {boolean} activeOnly - Si es true, solo devuelve dispositivos activos
   */
  async getDevices(activeOnly = false) {
    const response = await this.client.get('/api/v1/devices/', {
      params: { active_only: activeOnly }
    });
    return response.data;
  }

  /**
   * Obtiene los dispositivos activos (vistos recientemente)
   * @param {number} thresholdMinutes - Considerar activo si se ha visto dentro de N minutos
   */
  async getActiveDevices(thresholdMinutes = 60) {
    const response = await this.client.get('/api/v1/devices/active', {
      params: { threshold_minutes: thresholdMinutes }
    });
    return response.data;
  }

  /**
   * Obtiene detalles y estadísticas del dispositivo
   * @param {string} deviceId - Identificador del dispositivo
   */
  async getDeviceStats(deviceId) {
    const response = await this.client.get(`/api/v1/devices/${deviceId}/stats`);
    return response.data;
  }

  /**
   * Registra un nuevo dispositivo
   * @param {object} deviceData - {device_id, name, location}
   */
  async registerDevice(deviceData) {
    const response = await this.client.post('/api/v1/devices/register', deviceData);
    return response.data;
  }

  // ============= HEALTH & SYSTEM =============

  /**
   * Health check endpoint
   */
  async checkHealth() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      return { status: 'error', message: error.message };
    }
  }

  /**
   * Obtiene información sobre la API
   */
  async getApiInfo() {
    const response = await this.client.get('/');
    return response.data;
  }
}

export default new ApiService();
