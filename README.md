# Humberto 954

Documentación de la casa de Humberto 1º 954/58, Punta Alta, a partir de los planos originales de 1965.

## Contenido

- **[Visor 3D del tanque de agua](tanque/)**: tanque de hormigón armado de 1.000 L. Se puede girar, cortar, ver la armadura y mover el nivel de agua para calcular los litros. Incluye dimensiones, capacidad, peso y puntos a revisar.
- **[Recorrido 3D](recorrido/)**: maqueta de las dos plantas armada desde el DXF, con modo para caminar (teclado o joystick en el celular) y minimapa. Se regenera con `python3 tools/extraer_3d.py plano/Humberto954_plano.dxf recorrido/casa.json && python3 tools/build_recorrido.py`.
- **[Plano digitalizado](plano/)**: plantas baja y alta redibujadas en DXF (metros, por capas) y su vista en PDF.

Con GitHub Pages activo, el sitio queda en `https://imprezwag.github.io/humberto-954/`.

## Aviso

Los modelos y planos están redibujados desde copias escaneadas de 1965. No son un relevamiento: medir en obra antes de usarlos para obra o compras.
