Interfaz gráfica para el Cliente de Ataque (5x5)
===============================================

Este archivo provee una GUI simple para el cliente de ataque naval.

Archivos añadidos:
- `fsm_client_gui.py` : Interfaz Tkinter que carga `NavalClientFSM` desde `fsm-client_ataque.py`.

Cómo usar
--------
1. Asegúrate de que el servidor (`fsm-server_flota.py`) esté en ejecución o disponible.
2. Ejecuta la GUI desde la carpeta del proyecto:

```bash
python3 fsm_client_gui.py
```

Nota: en entornos sin servidor gráfico (DISPLAY) la GUI no se iniciará.

Pruebas rápidas
---------------
- Para comprobar sintaxis sin abrir la GUI:

```bash
python3 -m py_compile fsm_client_gui.py
```
