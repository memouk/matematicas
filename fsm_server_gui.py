#!/usr/bin/env python3
"""
Interfaz gráfica para `fsm-server_flota.py`.
- Permite ingresar IP y puerto.
- Muestra tablero 5x5 (A1..E5) y permite colocar un Destroyer (una celda).
- Botones para iniciar/detener el servidor (se ejecuta en hilo separado).

Nota: el módulo del servidor tiene un guion en el nombre de archivo
`fsm-server_flota.py`, así que lo cargamos dinámicamente usando importlib.
"""
import os
import threading
import tkinter as tk
from tkinter import messagebox
import importlib.util

# Cargar dinámicamente el módulo que contiene NavalServerFSM
MODULE_PATH = os.path.join(os.path.dirname(__file__), 'fsm-server_flota.py')

spec = importlib.util.spec_from_file_location('fsm_server_flota_mod', MODULE_PATH)
fsm_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fsm_mod)
NavalServerFSM = fsm_mod.NavalServerFSM

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('FSM - Servidor de Flota (GUI)')

        self.servidor = NavalServerFSM()
        self.server_thread = None

        # Top frame: IP / Port
        top = tk.Frame(root)
        top.pack(padx=10, pady=6, anchor='w')

        tk.Label(top, text='IP:').grid(row=0, column=0)
        self.ip_var = tk.StringVar(value=self.servidor.host)
        self.ip_entry = tk.Entry(top, textvariable=self.ip_var, width=15)
        self.ip_entry.grid(row=0, column=1, padx=(0,10))

        tk.Label(top, text='Puerto:').grid(row=0, column=2)
        self.port_var = tk.StringVar(value=str(self.servidor.port))
        self.port_entry = tk.Entry(top, textvariable=self.port_var, width=6)
        self.port_entry.grid(row=0, column=3, padx=(0,10))

        self.start_btn = tk.Button(top, text='Iniciar Servidor', command=self.start_server)
        self.start_btn.grid(row=0, column=4, padx=(0,6))

        self.stop_btn = tk.Button(top, text='Detener Servidor', command=self.stop_server, state='disabled')
        self.stop_btn.grid(row=0, column=5)

        # Ship placement controls
        place_frame = tk.Frame(root)
        place_frame.pack(padx=10, pady=(4,6), anchor='w')

        tk.Label(place_frame, text='Barco:').grid(row=0, column=0)
        self.selected_ship_var = tk.StringVar(value='D')
        ship_menu = tk.OptionMenu(place_frame, self.selected_ship_var, 'D', 'SS', 'LLL')
        ship_menu.config(width=5)
        ship_menu.grid(row=0, column=1, padx=(4,8))

        tk.Label(place_frame, text='Orientación:').grid(row=0, column=2)
        self.orientation_var = tk.StringVar(value='H')
        orient_menu = tk.OptionMenu(place_frame, self.orientation_var, 'H', 'V')
        orient_menu.config(width=3)
        orient_menu.grid(row=0, column=3, padx=(4,8))

        tk.Button(place_frame, text='Limpiar flota', command=self.clear_fleet).grid(row=0, column=4, padx=(6,0))

        # Status
        self.status_var = tk.StringVar(value='Estado: detenido')
        tk.Label(root, textvariable=self.status_var).pack(anchor='w', padx=10)

        # Board frame
        board_frame = tk.Frame(root)
        board_frame.pack(padx=10, pady=8)

        self.buttons = {}
        rows = ['A', 'B', 'C', 'D', 'E']
        cols = ['1', '2', '3', '4', '5']

        # Column headers
        header = tk.Frame(board_frame)
        header.grid(row=0, column=0, columnspan=6)

        # Build grid of buttons (with label row/col)
        tk.Label(board_frame, text=' ').grid(row=1, column=0)
        for j, c in enumerate(cols, start=1):
            tk.Label(board_frame, text=c, width=4).grid(row=1, column=j)

        for i, r in enumerate(rows, start=2):
            tk.Label(board_frame, text=r, width=2).grid(row=i, column=0)
            for j, c in enumerate(cols, start=1):
                pos = f"{r}{c}"
                btn = tk.Button(board_frame, text='~', width=4, command=lambda p=pos: self.toggle_cell(p))
                btn.grid(row=i, column=j, padx=2, pady=2)
                self.buttons[pos] = btn

        # Después de construir botones, sincronizar con el tablero del servidor
        self.refresh_board()

        # Info / legend
        legend = tk.Frame(root)
        legend.pack(padx=10, pady=(0,8), anchor='w')
        tk.Label(legend, text='Leyenda: D = Destroyer, SS = Submarino (2), LLL = Acorazado (3), ~ = agua, X = impacto, 0 = fallo (agua)').pack(side='left')
        tk.Button(legend, text='Refrescar flota', command=self.refresh_board).pack(side='left', padx=(8,0))

        # Bind close
        # Iniciar polling para refrescar tablero automáticamente (muestra impactos recibidos por el servidor)
        self.root.after(500, self._poll_server)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def toggle_cell(self, pos):
        """Colocar el Destroyer en la celda seleccionada (solo 1 permitido)."""
        ship_choice = self.selected_ship_var.get()
        orient = self.orientation_var.get()

        # Map GUI choice to internal type
        tipo_map = {'D': 'D', 'SS': 'S', 'LLL': 'L'}
        tipo = tipo_map.get(ship_choice, 'D')

        # If placing single-cell Destroyer
        if tipo == 'D':
            servidor_tab = self.servidor.tablero
            current = next((p for p, v in servidor_tab.items() if v == 'D'), None)

            if current == pos:
                if messagebox.askyesno('Quitar', f'Quitar Destroyer de {pos}?'):
                    # For simplicity recreate server instance as before
                    self.servidor = NavalServerFSM()
                    self.refresh_board()
                    self.status_var.set('Estado: flota removida')
                return

            if current and current != pos:
                if not messagebox.askyesno('Mover', f'Mover Destroyer de {current} a {pos}?'):
                    return

            # No permitir sobre otros barcos
            if self.servidor.tablero.get(pos) in ('S', 'L'):
                messagebox.showerror('Error', f'No se puede colocar Destroyer sobre otro barco en {pos}.')
                return

            ok = self.servidor.colocar_flota(pos)
            if ok:
                self.refresh_board()
                self.status_var.set(f'Destroyer colocado en {pos}')
            else:
                messagebox.showerror('Error', f'No se pudo colocar Destroyer en {pos}.')
            return

        # Para barcos multi-celda (SS -> longitud 2, L -> longitud 3)
        length = 2 if tipo == 'S' else 3

        # Calcular posiciones a partir de pos y orientación
        row = pos[0]
        col = int(pos[1])
        rows = ['A', 'B', 'C', 'D', 'E']

        positions = []
        try:
            if orient == 'H':
                # Avanzar columnas
                for offset in range(length):
                    c = col + offset
                    positions.append(f"{row}{c}")
            else:
                # Vertical: avanzar filas
                start_idx = rows.index(row)
                for offset in range(length):
                    r = rows[start_idx + offset]
                    positions.append(f"{r}{col}")
        except Exception:
            messagebox.showerror('Error', 'Colocación fuera del tablero')
            return

        # Validar solapamientos y existencia
        for p in positions:
            if p not in self.buttons:
                messagebox.showerror('Error', f'Posición inválida {p} en la colocación')
                return
            if self.servidor.tablero.get(p) is not None:
                messagebox.showerror('Error', f'Celda {p} ya ocupada')
                return

        # Evitar múltiples instancias del mismo tipo
        if self.servidor.ships.get(tipo):
            if not messagebox.askyesno('Reemplazar', f'Ya existe un {ship_choice}. ¿Reemplazarlo?'):
                return
            # Quitar existente del mismo tipo
            for p in list(self.servidor.ships.get(tipo)):
                self.servidor.tablero[p] = None
                self.servidor.ship_cells.discard(p)
            self.servidor.ships[tipo].clear()

        ok = self.servidor.colocar_barco(tipo, positions)
        if ok:
            self.refresh_board()
            self.status_var.set(f'{ship_choice} colocado en {positions}')
        else:
            messagebox.showerror('Error', 'No se pudo colocar el barco')

    def clear_fleet(self):
        """Limpia la flota en el servidor y refresca la GUI."""
        if messagebox.askyesno('Limpiar', '¿Desea quitar todos los barcos del tablero?'):
            self.servidor.limpiar_flota()
            self.refresh_board()
            self.status_var.set('Flota limpiada')

    def refresh_board(self):
        """Actualizar visualmente los botones según el tablero y los impactos del servidor."""
        for pos, btn in self.buttons.items():
            # Priorizar impactos
            if self.servidor.impactos.get(pos) == 'X':
                btn.config(text='X')
            elif self.servidor.impactos.get(pos) == 'O':
                btn.config(text='0')
            else:
                v = self.servidor.tablero.get(pos)
                if v == 'D':
                    btn.config(text='D')
                elif v == 'S':
                    btn.config(text='SS')
                elif v == 'L':
                    btn.config(text='LLL')
                else:
                    btn.config(text='~')

    def _poll_server(self):
        """Polling periódico: refresca la vista del tablero para mostrar impactos que llegan desde el hilo del servidor."""
        try:
            self.refresh_board()
        finally:
            # Reprogramar
            self.root.after(500, self._poll_server)

    def start_server(self):
        # Validar IP y puerto
        ip = self.ip_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror('Puerto inválido', 'Ingrese un número de puerto válido')
            return

        # Setear en la instancia
        self.servidor.host = ip
        self.servidor.port = port

        # Iniciar hilo del servidor
        if self.server_thread and self.server_thread.is_alive():
            messagebox.showinfo('Servidor', 'El servidor ya está corriendo')
            return

        def run_server():
            try:
                self.status_var.set(f'Estado: escuchando en {ip}:{port}')
                self.servidor.iniciar_servidor()
            except Exception as e:
                print('Excepción en servidor:', e)
            finally:
                self.status_var.set('Estado: detenido')
                self.start_btn.config(state='normal')
                self.stop_btn.config(state='disabled')

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_var.set(f'Estado: iniciando servidor en {ip}:{port} (ver consola)')

    def stop_server(self):
        # Intentar cerrar el socket del servidor para detener el loop
        try:
            if self.servidor.server_socket:
                self.servidor.server_socket.close()
                self.status_var.set('Estado: detenido (socket cerrado)')
            else:
                self.status_var.set('Estado: detenido (no había socket)')
        except Exception as e:
            messagebox.showwarning('Detener servidor', f'Error al detener: {e}')
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def on_close(self):
        # Intentar apagar servidor antes de salir
        if messagebox.askyesno('Salir', '¿Desea detener el servidor y salir?'):
            try:
                if self.servidor.server_socket:
                    self.servidor.server_socket.close()
            except Exception:
                pass
            self.root.destroy()


def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
