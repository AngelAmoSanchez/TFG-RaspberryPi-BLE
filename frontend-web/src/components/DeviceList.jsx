import React from 'react';
import { CheckCircle, XCircle, MapPin, Calendar } from 'lucide-react';

const DeviceList = ({ devices, loading }) => {
  if (loading) {
    return <div className="text-center py-4 text-gray-500">Cargando dispositivos...</div>;
  }

  if (devices.length === 0) {
    return <div className="text-center py-4 text-gray-400">No hay dispositivos registrados</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              ID / Nombre
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Ubicación
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Última Conexión
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {devices.map((device) => (
            <tr key={device.device_id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                {device.is_active ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500" />
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {device.name || device.device_id}
                  </div>
                  {device.name && (
                    <div className="text-xs text-gray-500">{device.device_id}</div>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center text-sm text-gray-600">
                  <MapPin className="w-4 h-4 mr-1" />
                  {device.location || 'No especificado'}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center text-sm text-gray-600">
                  <Calendar className="w-4 h-4 mr-1" />
                  {device.last_seen
                    ? new Intl.DateTimeFormat('es-ES', {
                      dateStyle: 'short',
                      timeStyle: 'medium',
                      timeZone: 'Europe/Madrid',
                    }).format(new Date(device.last_seen))
                    : 'Nunca'
                  }
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DeviceList;
