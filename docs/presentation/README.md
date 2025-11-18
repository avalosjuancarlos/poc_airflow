# 📊 Presentación del Proyecto

## 🎯 Cómo Usar la Presentación

### Opción 1: Abrir en el Navegador (Recomendado)

1. Abre el archivo `index.html` en tu navegador:
   ```bash
   # Desde la raíz del proyecto
   open docs/presentation/index.html
   
   # O en Linux
   xdg-open docs/presentation/index.html
   
   # O en Windows
   start docs/presentation/index.html
   ```

2. **Navegación:**
   - **Flechas** ← → : Navegar entre slides
   - **Espacio**: Siguiente slide
   - **ESC**: Vista general de todas las slides
   - **F**: Modo pantalla completa
   - **S**: Modo presentador (con notas)

### Opción 2: Servidor Local

Para mejor experiencia, sirve el archivo con un servidor HTTP:

```bash
# Python 3
cd docs/presentation
python3 -m http.server 8000

# O con Node.js (si tienes http-server instalado)
npx http-server -p 8000

# Luego abre en el navegador:
# http://localhost:8000
```

### Opción 3: Modo Presentación

1. Abre `index.html` en el navegador
2. Presiona **F** para entrar en modo pantalla completa
3. Usa las flechas o espacio para navegar

## ⌨️ Atajos de Teclado

| Tecla | Acción |
|-------|--------|
| `→` o `Espacio` | Siguiente slide |
| `←` | Slide anterior |
| `ESC` | Vista general |
| `F` | Pantalla completa |
| `S` | Modo presentador |
| `O` | Vista general (overview) |

## 📝 Notas

- La presentación usa **Reveal.js** cargado desde CDN (no requiere instalación)
- Funciona completamente offline una vez cargada
- Compatible con todos los navegadores modernos
- Responsive: se adapta a diferentes tamaños de pantalla

## 🔄 Actualizar la Presentación

Si modificas `PROJECT_PRESENTATION.md`, necesitarás actualizar manualmente `index.html` para reflejar los cambios.

---

**¡Disfruta presentando el proyecto!** 🚀

