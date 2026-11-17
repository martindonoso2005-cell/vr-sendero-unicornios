# Sendero de Unicornios VR

Entorno virtual 360° interactivo hecho con [A-Frame](https://aframe.io) 1.7. Cuatro panoramas equirectangulares (4096×2048) de un sendero con unicornios se proyectan sobre esferas:

- **Esfera envolvente** (radio 120, cara interior): el mundo en el que estás.
- **Cuatro esferas-portal** flotando frente a ti, cada una texturizada con un panorama. Al seleccionarlas viajas a ese mundo con un fundido.

| Mundo | Archivo |
|---|---|
| Día arcoíris | `assets/panoramas/dia_arcoiris.jpg` |
| Atardecer mágico | `assets/panoramas/atardecer_magico.jpg` |
| Noche estrellada | `assets/panoramas/noche_estrellada.jpg` |
| Bosque pastel | `assets/panoramas/bosque_algodon_pastel.jpg` |

## Controles

- **Escritorio:** arrastra para mirar, WASD para caminar (limitado al centro), clic en una esfera o teclas 1–4.
- **Visor VR (Quest, etc.):** botón VR, apunta con el láser de cualquier mando y pulsa el gatillo.
- **Móvil / Cardboard:** mira fijo una esfera 1,5 s (cursor por mirada).

## Ejecutar en local

Necesita un servidor HTTP (las texturas no cargan con `file://`):

```bash
python -m http.server 8000
```

y abre http://localhost:8000.

## Estructura

```
index.html              escena A-Frame
js/componentes.js       gestor-mundos, esfera-mundo, destellos, movement-bounds
assets/panoramas/       las 4 imágenes equirectangulares
herramientas/generar_panoramas.py   script (numpy + Pillow) que genera los panoramas
```

Para regenerar los panoramas: `pip install numpy pillow` y `python herramientas/generar_panoramas.py 4096`.
