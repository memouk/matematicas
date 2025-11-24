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

        # Info / legend
        legend = tk.Frame(root)
        legend.pack(padx=10, pady=(0,8), anchor='w')
        tk.Label(legend, text='Leyenda: D = Destroyer (visible en servidor), ~ = agua, X = impacto, O = fallo').pack()

        # Bind close
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def toggle_cell(self, pos):
        """Colocar el Destroyer en la celda seleccionada (solo 1 permitido)."""
        # Si ya hay colocado en servidor, quitarlo visualmente
        # Nuestra NavalServerFSM solo soporta un Destroyer y la función colocar_flota coloca y setea estado.
        # Para simplicidad, si ya colocamos, preguntamos si desea mover.
        if any(self.buttons[p]['text'] == 'D' for p in self.buttons):
            current = next(p for p in self.buttons if self.buttons[p]['text'] == 'D')
            if current == pos:
                # Desea quitar
                if messagebox.askyesno('Quitar', f'Quitar Destroyer de {pos}?'):
                    # No hay método para quitar en la clase original; recreamos la instancia de servidor para resetear.
                    self.servidor = NavalServerFSM()
                    # Reset textos
                    for b in self.buttons.values():
                        b.config(text='~')
                    self.status_var.set('Estado: flota removida')
                return
            else:
                if not messagebox.askyesno('Mover', f'Mover Destroyer de {current} a {pos}?'):
                    return
                # Reset previous visual
                self.buttons[current].config(text='~')

        # Intentar colocar en servidor
        ok = self.servidor.colocar_flota(pos)
        if ok:
            # Visualmente marcar D
            for p in self.buttons:
                self.buttons[p].config(text='~')
            self.buttons[pos].config(text='D')
            self.status_var.set(f'Destroyer colocado en {pos}')
        else:
            messagebox.showerror('Error', f'No se pudo colocar Destroyer en {pos}.')

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
