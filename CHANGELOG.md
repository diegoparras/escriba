# Changelog

Todos los cambios importantes de Escriba se anotan aca. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es/1.0.0/); versionado semantico.
La version instalada vive en el archivo `VERSION` y cada deploy tiene que tener su seccion.

## [1.15.3] - 2026-11-20

### Corregido
- La imagen ya no arrastra una variable `APP_VERSION` vacia del build anterior (el build daba
  un aviso). La version sigue saliendo del archivo `VERSION`.

## [1.15.2] - 2026-11-20

### Nuevo
- Cada deploy dice su version y que cambia: es lo primero que escribe el contenedor
  en los registros de EasyPanel (servicio > Resumen > Registros).
- Aviso **Novedades** en la web: aparece una sola vez al entrar despues de una
  actualizacion. Tambien se abre desde el menu (Novedades) y desde "Acerca de" (Que cambio).
- Cada version publicada queda como Release en GitHub con estas mismas notas, y la imagen
  se etiqueta tambien con su numero (`ghcr.io/diegoparras/escriba:1.15.2`).

### Cambiado
- La version sale del archivo `VERSION` (antes, del ultimo tag de git): el numero que se ve
  en "Acerca de" es el mismo del Release y de la imagen.
- CI: acciones de GitHub actualizadas a sus versiones que corren sobre Node 24 (checkout v7,
  setup-python v7, login v4, metadata v6, setup-buildx v4, build-push v7).
