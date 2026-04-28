import React from 'react';
import { Wifi, WifiOff } from 'lucide-react';

const ConnectionStatus = ({ connected }) => {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
      connected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
    }`}>
      {connected ? (
        <>
          <Wifi className="w-4 h-4" />
          <span className="text-sm font-medium">Conectado</span>
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4" />
          <span className="text-sm font-medium">Desconectado</span>
        </>
      )}
    </div>
  );
};

export default ConnectionStatus;
