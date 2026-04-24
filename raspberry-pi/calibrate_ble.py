#!/usr/bin/env python3
"""
Script de Calibración BLE (Versión sin colores)
Detecta dispositivos BLE y muestra RSSI en tiempo real para ajustar umbrales
"""
import asyncio
from datetime import datetime
from bleak import BleakScanner
from collections import defaultdict
from zoneinfo import ZoneInfo

SPAIN_TZ = ZoneInfo("Europe/Madrid")


def classify_distance(rssi):
    """Clasifica distancia según RSSI"""
    if rssi >= -50:
        return "MUY CERCA (<1m)"
    elif rssi >= -60:
        return "CERCA (1-2m)"
    elif rssi >= -70:
        return "MEDIO (2-4m)"
    elif rssi >= -80:
        return "LEJOS (4-8m)"
    else:
        return "MUY LEJOS (>8m)"


async def main():
    print("=" * 70)
    print("  CALIBRACIÓN BLE - Sistema de Conteo de Personas")
    print("=" * 70)
    
    duration = 20
    print(f"Escaneando dispositivos BLE durante {duration} segundos...")
    print("INSTRUCCIONES:")
    print("  1. Acerca/aleja tu dispositivo (Mi Band, móvil, etc.)")
    print("  2. Observa cómo cambia el RSSI según la distancia")
    print("  3. Anota los valores que ves a diferentes distancias")
    print()
    
    devices_history = defaultdict(lambda: {
        'name': 'Unknown',
        'rssi_values': [],
        'first_seen': None,
        'last_seen': None
    })
    
    detection_count = 0
    
    def callback(device, advertisement_data):
        nonlocal detection_count
        detection_count += 1
        
        rssi = advertisement_data.rssi
        name = device.name or "Unknown"
        addr = device.address
        
        # Actualizar historial
        if devices_history[addr]['first_seen'] is None:
            devices_history[addr]['first_seen'] = datetime.now(SPAIN_TZ)
        
        devices_history[addr]['name'] = name
        devices_history[addr]['rssi_values'].append(rssi)
        devices_history[addr]['last_seen'] = datetime.now(SPAIN_TZ)
        
        # Clasificar
        dist_label = classify_distance(rssi)
        
        # Mostrar en tiempo real
        print(f"[{addr[:8]}...] {name:25s} | RSSI: {rssi:4d} dBm | {dist_label}")
    
    # Escanear
    scanner = BleakScanner(detection_callback=callback)
    
    start_time = datetime.now(SPAIN_TZ)
    await scanner.start()
    await asyncio.sleep(duration)
    await scanner.stop()
    end_time = datetime.now(SPAIN_TZ)
    
    # Resultados
    print()
    print("=" * 70)
    print("  RESUMEN DE CALIBRACIÓN BLE")
    print("=" * 70)
    print()
    
    print(f"  Duración: {(end_time - start_time).total_seconds():.1f}s")
    print(f"  Detecciones totales: {detection_count}")
    print(f"  Dispositivos únicos: {len(devices_history)}")
    print()
    
    if not devices_history:
        print("X - No se detectaron dispositivos BLE")
        print()
        print("Posibles causas:")
        print("  - No hay dispositivos BLE cerca")
        print("  - Bluetooth apagado en los dispositivos")
        print("  - Móviles no emiten BLE (normal)")
        print("  - Intenta con: Mi Band, AirPods, Smartwatch")
        return
    
    # Ordenar por RSSI máximo
    sorted_devices = sorted(
        devices_history.items(),
        key=lambda x: max(x[1]['rssi_values']),
        reverse=True
    )
    
    print("============== DISPOSITIVOS DETECTADOS (ordenados por señal) ==============")
    print()
    
    for addr, data in sorted_devices:
        name = data['name']
        rssi_vals = data['rssi_values']
        avg_rssi = sum(rssi_vals) / len(rssi_vals)
        max_rssi = max(rssi_vals)
        min_rssi = min(rssi_vals)
        
        print(f"{'─' * 70}")
        print(f"== {name} ({addr}) ==")
        print(f"   RSSI Promedio:  {avg_rssi:6.1f} dBm")
        print(f"   RSSI Máximo:    {max_rssi:6d} dBm  (más cerca detectado)")
        print(f"   RSSI Mínimo:    {min_rssi:6d} dBm  (más lejos detectado)")
        print(f"   Detecciones:    {len(rssi_vals):6d}")
        print(f"   Permanencia:    {(data['last_seen'] - data['first_seen']).total_seconds():.1f}s")
    
    print()
    
    # Calcular umbrales recomendados
    print("=" * 70)
    print("  UMBRALES RECOMENDADOS PARA config.py")
    print("=" * 70)
    print()
    
    all_rssi = []
    for data in devices_history.values():
        all_rssi.extend(data['rssi_values'])
    
    if all_rssi:
        all_rssi.sort(reverse=True)
        
        # Percentiles
        p30 = all_rssi[int(len(all_rssi) * 0.3)]  # Top 30% = cerca
        p70 = all_rssi[int(len(all_rssi) * 0.7)]  # Top 70% = medio
        
        print(f"Basado en {len(all_rssi)} mediciones:")
        print()
        print("@dataclass")
        print("class ZoneConfig:")
        print('    """Configuración de umbrales de zonas"""')
        print(f"    near_threshold: int = {p30}    # Top 30% señales (cercanas)")
        print(f"    medium_threshold: int = {p70}  # Top 70% señales (medias)")
        print(f"    # far = resto (peor que {p70})")
        print()
        
        # Distribución
        print("============== DISTRIBUCIÓN DE SEÑALES ==============")
        print()
        
        ranges = [
            (-50, float('inf'), "MUY CERCA (<1m)"),
            (-60, -50, "CERCA (1-2m)"),
            (-70, -60, "MEDIO (2-4m)"),
            (-80, -70, "LEJOS (4-8m)"),
            (float('-inf'), -80, "MUY LEJOS (>8m)")
        ]
        
        for min_rssi, max_rssi, label in ranges:
            if max_rssi == float('inf'):
                count = sum(1 for r in all_rssi if r >= min_rssi)
            elif min_rssi == float('-inf'):
                count = sum(1 for r in all_rssi if r < max_rssi)
            else:
                count = sum(1 for r in all_rssi if min_rssi <= r < max_rssi)
            
            percentage = (count / len(all_rssi)) * 100
            bar = '█' * int(percentage / 2)
            
            print(f"  {label:20s} {count:4d} ({percentage:5.1f}%) {bar}")
        
        print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCalibración interrumpida por el usuario")