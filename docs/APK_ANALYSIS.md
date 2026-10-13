# Analisis seguro de la APK Cubitt Pro

Objetivo: buscar pistas de VITA AI, BLE, firmware u OTA sin modificar nada.

## Herramientas

- Android Studio, opcional.
- `jadx-gui`, para leer codigo Java/Kotlin de la APK.
- `tools/scan_cubitt_apk.ps1`, para un primer escaneo local de cadenas.

## Obtener la APK

Usa una copia legitima de la app `Cubitt Pro` instalada en tu telefono o descargada desde una fuente que tengas derecho a usar.

App esperada:

```text
Nombre: Cubitt Pro
Package: com.cubittpros.wear
```

Si tu telefono esta conectado por ADB:

```powershell
.\tools\pull_cubitt_apk.ps1
```

## Escaneo rapido con PowerShell

Coloca la APK en una carpeta local, por ejemplo:

```text
apks/cubitt-pro.apk
```

Ejecuta desde la raiz del proyecto:

```powershell
.\tools\scan_cubitt_apk.ps1 -ApkPath .\apks\cubitt-pro.apk
```

El script generara un reporte en:

```text
analysis/
```

Busca especialmente:

- URLs `https://...`
- `vita`
- `voice`
- `speech`
- `ota`
- `dfu`
- `firmware`
- `upgrade`
- `gatt`
- `uuid`
- `bluetooth`
- nombres de SDK o fabricantes

## Analisis con jadx-gui

1. Abre `jadx-gui`.
2. Carga la APK.
3. Usa busqueda global.
4. Busca las mismas palabras clave.
5. Si encuentras clases de OTA, BLE o VITA, anota:
   - Nombre de clase.
   - Paquete.
   - UUIDs.
   - URLs.
   - Nombres de archivos `.bin`, `.fw`, `.zip` o `.json`.

## Que estamos buscando

La pregunta clave es:

```text
Cuando hablas con VITA AI desde el reloj, el audio/comando pasa por Cubitt Pro?
```

Si la respuesta es si, se podria investigar un reemplazo hacia Gemini sin firmware.

Si la respuesta es no, y VITA esta dentro del firmware o en servidores cerrados, el reemplazo real dependeria de firmware.

## Siguiente paso para firmware

Sigue `docs/FIRMWARE_RESEARCH.md` para capturar logs, buscar firmware cacheado e identificar el mecanismo OTA antes de intentar cualquier modificacion.
