import axios from 'axios';

// Configuración base del cliente HTTP
class ApiClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /**
   * Obtiene estadísticas por hora para una fecha en concreto
   * @param {string} date - Fecha (en formato YYYY-MM-DD)
   */
  async getHourlyStatistics(date) {
    try {
      const response = await this.client.get('/api/statistics/hourly', {
        params: { date }
      });
      return response.data;
    } catch (error) {
      console.error('ERROR - Error obteniendo estadísticas por hora:', error);
      throw error;
    }
  }

  /**
   * Obtiene estadísticas diarias para un rango de fechas
   * @param {string} startDate - Fecha de inicio
   * @param {string} endDate - Fecha de fin
   */
  async getDailyStatistics(startDate, endDate) {
    try {
      const response = await this.client.get('/api/statistics/daily', {
        params: { start_date: startDate, end_date: endDate }
    });
    return response.data;
  } catch (error) {
      console.error('ERROR - Error obteniendo estadísticas diarias:', error);
      throw error;
    }
  }

  /**
   * Obtiene resumen por zonas (de la última hora) actualizado en tiempo real
  */
  async getCurrentSummary() {
    try {
      const response = await this.client.get('/api/statistics/current');
      return response.data;
    } catch (error) {
      console.error('ERROR - Error obteniendo resumen actual:', error);
      throw error;
    }
  }

  /**
   * Permite exportar los datos en CSV
   * @param {string} startDate 
   * @param {string} endDate 
  */
  async exportCSV(startDate, endDate) {
    try {
      const response = await this.client.get('/api/export/csv', {
        params: { start_date: startDate, end_date: endDate },
        responseType: 'blob'
      });
      return response.data;
    } catch (error) {
      console.error('ERROR - Error exportando CSV:', error);
      throw error;
    }
  }

  /**
   * Health check - Permite ver si el sistema está funcionando
   */
  async checkHealth() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      return { status: 'error' };
    }
  }
}

export default new ApiClient();
