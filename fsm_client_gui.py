#!/usr/bin/env python3
"""
GUI para el cliente de ataque naval (5x5)

Permite ingresar IP y puerto del servidor y atacar casillas A1..E5
mediante una interfaz gráfica sencilla con Tkinter.

Este módulo carga la clase `NavalClientFSM` desde
`fsm-client_ataque.py` (archivo del cliente existente) y la usa para
enviar ataques al servidor.
"""

import os
import threading
import importlib.util
import tkinter as tk
from tkinter import messagebox


def load_client_class():
    """Carga NavalClientFSM desde el archivo `fsm-client_ataque.py`."""
    base = os.path.dirname(__file__)
    path = os.path.join(base, 'fsm-client_ataque.py')
    spec = importlib.util.spec_from_file_location('fsm_client_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.NavalClientFSM


class NavalClientGUI:
    def __init__(self, master=None):
        self.master = master or tk.Tk()
        self.master.title('Cliente de Ataque - GUI (5x5)')

        # Cargar la clase cliente
        ClientClass = load_client_class()
        self.client = ClientClass()

        # Frame de configuración
        cfg = tk.Frame(self.master)
        cfg.pack(padx=8, pady=6, anchor='w')

        tk.Label(cfg, text='Servidor IP:').grid(row=0, column=0, sticky='w')
        self.ip_entry = tk.Entry(cfg, width=15)
        self.ip_entry.insert(0, self.client.server_host)
        self.ip_entry.grid(row=0, column=1, padx=4)

        tk.Label(cfg, text='Puerto:').grid(row=0, column=2, sticky='w')
        self.port_entry = tk.Entry(cfg, width=6)
        self.port_entry.insert(0, str(self.client.server_port))
        self.port_entry.grid(row=0, column=3, padx=4)

        self.connect_btn = tk.Button(cfg, text='Configurar', command=self.configurar_servidor)
        self.connect_btn.grid(row=0, column=4, padx=6)

        # Frame del tablero
        board_frame = tk.Frame(self.master)
        board_frame.pack(padx=8, pady=6)

        # Obtener filas/columnas del cliente (suponemos que existen)
        self.filas = getattr(self.client, 'filas', ['A', 'B', 'C', 'D', 'E'])
        self.columnas = getattr(self.client, 'columnas', ['1', '2', '3', '4', '5'])

        # Diccionario de botones por coordenada
        self.buttons = {}

        # Cabeceras de columna
        for j, col in enumerate([''] + self.columnas):
            lbl = tk.Label(board_frame, text=col, width=4)
            lbl.grid(row=0, column=j)

        for i, fila in enumerate(self.filas, start=1):
            # cabecera de fila
            lbl = tk.Label(board_frame, text=fila, width=3)
            lbl.grid(row=i, column=0)
            for j, col in enumerate(self.columnas, start=1):
                coord = f"{fila}{col}"
                btn = tk.Button(board_frame, text='~', width=4,
                                command=lambda c=coord: self.on_click(c))
                btn.grid(row=i, column=j, padx=2, pady=2)
                self.buttons[coord] = btn

        # Estado y control
        status_frame = tk.Frame(self.master)
        status_frame.pack(fill='x', padx=8, pady=(0,8))
        self.status_label = tk.Label(status_frame, text='Estado: listo')
        self.status_label.pack(side='left')

        self.ataques_label = tk.Label(status_frame, text=f'Ataques: {self.client.ataques_realizados}')
        self.ataques_label.pack(side='right')

    def configurar_servidor(self):
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        if ip:
            self.client.server_host = ip
        try:
            if port:
                self.client.server_port = int(port)
        except ValueError:
            messagebox.showerror('Puerto inválido', 'El puerto debe ser un número entero.')
            return

        self.status_label.config(text=f'Configurado a {self.client.server_host}:{self.client.server_port}')

    def on_click(self, coord):
        btn = self.buttons.get(coord)
        # Evitar doble envío mientras se procesa
        btn.config(state='disabled')
        self.status_label.config(text=f'Enviando ataque {coord}...')

        # Ejecutar envío en hilo para no bloquear GUI
        t = threading.Thread(target=self._send_thread, args=(coord,))
        t.daemon = True
        t.start()

    def _send_thread(self, coord):
        try:
            resp = self.client.enviar_ataque(coord)
        except Exception as e:
            resp = None
            err = str(e)

        # Programar actualización de la GUI en el hilo principal
        self.master.after(0, lambda: self._after_attack(coord, resp))

    def _after_attack(self, coord, response):
        btn = self.buttons.get(coord)
        if response is None:
            # Error de conexión u otro
            messagebox.showerror('Error', f'No se recibió respuesta del servidor.')
            # Re-habilitar el botón para reintentar
            btn.config(state='normal')
            self.status_label.config(text='Error: sin respuesta')
            return

        # Procesar respuesta esperada en formato "COD:Mensaje"
        try:
            codigo, mensaje = response.split(':', 1)
        except Exception:
            messagebox.showwarning('Respuesta inválida', f'Respuesta inesperada: {response}')
            btn.config(state='normal')
            return

        # Actualizar contador
        self.ataques_label.config(text=f'Ataques: {self.client.ataques_realizados}')

        if '200' in codigo or '202' in codigo:
            # Impacto
            btn.config(text='X', bg='red', disabledforeground='white')
            btn.config(state='disabled')
            self.status_label.config(text=f'{coord}: {mensaje}')
        elif '404' in codigo:
            # Fallo
            btn.config(text='O', bg='light blue')
            btn.config(state='disabled')
            self.status_label.config(text=f'{coord}: {mensaje}')
        elif '409' in codigo:
            # Ataque repetido
            messagebox.showinfo('Repetido', f'{coord} ya fue atacado previamente.')
            # Marcar según lo que tiene el cliente (si hay marca)
            mark = self.client.tablero_ataques.get(coord, '~')
            if mark == 'X':
                btn.config(text='X', bg='red', state='disabled')
            elif mark == 'O':
                btn.config(text='O', bg='light blue', state='disabled')
            else:
                btn.config(state='normal')
            self.status_label.config(text=f'{coord}: {mensaje}')
        else:
            # Otros códigos
            self.status_label.config(text=f'{coord}: {response}')

    def run(self):
        self.master.mainloop()


def main():
    gui = NavalClientGUI()
    gui.run()


if __name__ == '__main__':
    main()
