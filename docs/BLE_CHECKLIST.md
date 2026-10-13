# Checklist BLE para Cubitt VIVA Pro 2

Objetivo: observar Bluetooth sin escribir datos ni modificar el reloj.

## Herramienta

Instala en Android:

```text
nRF Connect for Mobile
```

## Reglas

- No escribas valores en caracteristicas BLE.
- No ejecutes comandos DFU/OTA.
- Solo escanea, conecta si es necesario y toma capturas.
- Si aparece una opcion de `Write`, `Upload`, `DFU` o `Update`, no la uses todavia.

## Escaneo 1: reloj sin Cubitt Pro abierto

1. Cierra Cubitt Pro.
2. Abre `nRF Connect`.
3. Toca `Scan`.
4. Busca nombres como `Cubitt`, `VIVA`, `VIVA PRO`, o un dispositivo con senal fuerte.
5. Guarda captura de:
   - Nombre anunciado.
   - Direccion BLE o identificador.
   - RSSI.
   - Datos de advertising.

## Escaneo 2: reloj vinculado normalmente

1. Abre Cubitt Pro y conecta el reloj.
2. Vuelve a `nRF Connect`.
3. Repite el escaneo.
4. Compara si cambio el nombre, servicios o estado.

## Si puedes conectar desde nRF Connect

Documenta:

- Servicios GATT.
- UUIDs.
- Caracteristicas `Read`, `Notify`, `Indicate`, `Write`.
- Cualquier texto relacionado con:
  - `OTA`
  - `DFU`
  - `Firmware`
  - `Voice`
  - `AI`
  - `Audio`

## Formato para registrar resultados

Copia esto en tus notas:

```text
Modelo visible:
Nombre BLE:
Direccion/ID BLE:
Fecha:
Telefono Android:
Cubitt Pro abierto: si/no

Servicios:
- UUID:
  - Caracteristicas:
  - Permisos:
  - Notas:

Se observo OTA/DFU: si/no
Se observo voz/audio/AI: si/no
Capturas guardadas: si/no
```

## Interpretacion

- Si hay servicios de voz/audio, puede existir un flujo que pase por el telefono.
- Si solo hay salud/notificaciones, VITA AI probablemente esta mas cerrado.
- Si hay OTA/DFU, todavia no significa que podamos modificar firmware; faltan formato, firma, chip y recuperacion.
