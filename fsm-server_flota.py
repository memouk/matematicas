"""
FSM Naval Battle - Servidor de Defensa
-----------------------------------
Este programa implementa un servidor que maneja un autómata finito determinista (DFA)
para representar un sistema de defensa naval simplificado en una cuadrícula 2x2.

Autómata Finito para el Servidor:
--------------------------------
Q = {q0, q1, q2} : {Inicio, Flota_Intacta, Hundido}
Σ = {A1, A2, B1, B2} (Coordenadas de la cuadrícula 2x2)
q₀ = q0 (Inicio)
F = {q2} (Hundido - Estado de aceptación)
δ = Función de transición (depende de la ubicación del barco)
"""

import socket
import time

class NavalServerFSM:
    """
    Implementación de la Máquina de Estados Finitos para el servidor de defensa naval.
    """
    # Estados del autómata
    INICIO = 'q0'        # Estado inicial (colocación de flota)
    FLOTA_INTACTA = 'q1' # Flota colocada, sin impactos
    HUNDIDO = 'q2'       # Barco hundido (estado final/aceptación)
    
    def __init__(self):
        # Estado actual del autómata
        self.estado_actual = self.INICIO
        
        # Tamaño del tablero (2x2, 5x5)
        self.filas = 5
        self.columnas = 5

        # Tablero de juego (representado como diccionario para facilitar acceso)
        # Valores posibles en tablero (tipo interno): None (agua), 'D' (Destroyer), 'S' (Submarino), 'L' (Acorazado)
        self.tablero = {
            'A1': None, 'A2': None, 'A3': None, 'A4': None, 'A5': None,
            'B1': None, 'B2': None, 'B3': None, 'B4': None, 'B5': None,
            'C1': None, 'C2': None, 'C3': None, 'C4': None, 'C5': None,
            'D1': None, 'D2': None, 'D3': None, 'D4': None, 'D5': None,
            'E1': None, 'E2': None, 'E3': None, 'E4': None, 'E5': None
        }

        # Estado de impactos (para seguimiento visual)
        # Valores: '~' (sin atacar), 'O' (fallo/agua), 'X' (impacto)
        self.impactos = {
            'A1': '~', 'A2': '~', 'A3': '~', 'A4': '~', 'A5': '~',
            'B1': '~', 'B2': '~', 'B3': '~', 'B4': '~', 'B5': '~',
            'C1': '~', 'C2': '~', 'C3': '~', 'C4': '~', 'C5': '~',
            'D1': '~', 'D2': '~', 'D3': '~', 'D4': '~', 'D5': '~',
            'E1': '~', 'E2': '~', 'E3': '~', 'E4': '~', 'E5': '~'
        }

        # Historial de ataques (para evitar ataques repetidos)
        self.ataques_recibidos = set()

        # Estructura para manejar barcos multi-celda
        # ships -> mapa tipo -> conjunto de posiciones (ej: 'S': {'B1','B2'})
        self.ships = {
            'D': set(),  # Destroyer (1 celda)
            'S': set(),  # Submarino (2 celdas)
            'L': set()   # Acorazado (3 celdas)
        }

        # Conjunto de todas las celdas ocupadas por cualquier barco
        self.ship_cells = set()

        # Socket del servidor
        self.server_socket = None
        self.host = '' ##'localhost'  # Para propósitos educativos, usar localhost
        self.port = 5000         # Puerto por defecto

    # Nota: no colocar flota por defecto aquí. La GUI podrá colocar barcos manualmente.
    
    def colocar_flota(self, posicion_destroyer):
        """
        Coloca un barco (Destroyer) en el tablero.
        
        Args:
            posicion_destroyer: Posición del Destroyer (ej: 'A1')
        """
        # Validar posición
        if posicion_destroyer not in self.tablero:
            print(f"Posición {posicion_destroyer} inválida.")
            return False

        # Colocar el Destroyer (1 celda)
        self.tablero[posicion_destroyer] = 'D'
        self.ships['D'].add(posicion_destroyer)
        self.ship_cells.add(posicion_destroyer)

        # Cambiar estado a FLOTA_INTACTA
        self.estado_actual = self.FLOTA_INTACTA
        print(f"Destroyer colocado en {posicion_destroyer}")
        return True

    def _colocar_barcos_defecto(self):
        """
        Coloca por defecto un Submarino (2 celdas) y un Acorazado (3 celdas).
        Las posiciones elegidas son didácticas y fijas: Submarino en B1-B2, Acorazado en C1-C3.
        """
        # Submarino (2 casillas)
        subs = ['B1', 'B2']
        for p in subs:
            if p in self.tablero:
                self.tablero[p] = 'S'
                self.ships['S'].add(p)
                self.ship_cells.add(p)

        # Acorazado (3 casillas)
        acor = ['C1', 'C2', 'C3']
        for p in acor:
            if p in self.tablero:
                self.tablero[p] = 'L'
                self.ships['L'].add(p)
                self.ship_cells.add(p)

        if self.ship_cells:
            self.estado_actual = self.FLOTA_INTACTA
            print(f"Flota por defecto colocada: Submarino {subs}, Acorazado {acor}")

    def limpiar_flota(self):
        """Quita todos los barcos del tablero y resetea impactos/estado."""
        # Limpiar celdas ocupadas
        for pos in list(self.ship_cells):
            if pos in self.tablero:
                self.tablero[pos] = None
        # Reset estructuras
        for k in self.ships:
            self.ships[k].clear()
        self.ship_cells.clear()

        # Reset impactos
        for k in self.impactos:
            self.impactos[k] = '~'

        self.estado_actual = self.INICIO

    def colocar_barco(self, tipo, posiciones):
        """Coloca un barco de tipo dado en las posiciones listadas.

        Args:
            tipo: 'D', 'S' o 'L'
            posiciones: lista/iterable de posiciones (ej: ['B1','B2'])

        Returns:
            True si se colocó correctamente, False si hay conflicto o posición inválida.
        """
        # Validar tipo
        if tipo not in ('D', 'S', 'L'):
            print(f"Tipo de barco inválido: {tipo}")
            return False

        # Validar posiciones
        pos_list = list(posiciones)
        for p in pos_list:
            if p not in self.tablero:
                print(f"Posición inválida: {p}")
                return False
            if self.tablero[p] is not None:
                print(f"Posición ocupada: {p}")
                return False

        # Colocar
        for p in pos_list:
            self.tablero[p] = tipo
            self.ships[tipo].add(p)
            self.ship_cells.add(p)

        # Actualizar estado
        if self.ship_cells:
            self.estado_actual = self.FLOTA_INTACTA
        return True
    
    def mostrar_tablero(self):
        """
        Muestra el tablero actual del juego.
        """
        print("\nTablero de defensa (5x5):")
        # Usaremos ancho de columna fijo para mostrar etiquetas más largas (ej: 'SS','LLL')
        cols = ['1', '2', '3', '4', '5']
        print("  ", end="")
        for c in cols:
            print(f" {c} ", end="")
        print()
        print(" ┌────────────────────────────┐")

        for fila in ['A', 'B', 'C', 'D', 'E']:
            print(f"{fila}│", end="")
            for col in cols:
                pos = f"{fila}{col}"
                if self.impactos[pos] == 'X':
                    cel = ' X '
                elif self.impactos[pos] == 'O':
                    cel = ' O '
                else:
                    # Mostrar tipo de barco si existe
                    if self.tablero[pos] == 'D':
                        cel = ' D '
                    elif self.tablero[pos] == 'S':
                        cel = 'SS '
                    elif self.tablero[pos] == 'L':
                        cel = 'LLL'
                    else:
                        cel = ' ~ '
                print(cel, end="")
            print("│")

        print(" └────────────────────────────┘")
        print(" D: Destroyer, SS: Submarino (2), LLL: Acorazado (3), ~: Agua, O: Fallo, X: Impacto")
        
    def procesar_ataque(self, coordenada):
        """
        Procesa un ataque recibido y aplica la función de transición del autómata.
        
        Args:
            coordenada: Coordenada del ataque (ej: 'A1')
            
        Returns:
            Tuple: (código_respuesta, mensaje_detalle)
        """
        # Validar coordenada
        if coordenada not in self.tablero:
            return "404", "Coordenada inválida"
        
        # Verificar ataque repetido
        if coordenada in self.ataques_recibidos:
            return "409", "Atacado_Previamente"
        
        # Registrar el ataque
        self.ataques_recibidos.add(coordenada)
        
        # Función de transición δ según el estado actual y la entrada
        if self.estado_actual == self.INICIO:
            return "400", "Flota_No_Colocada"

        elif self.estado_actual == self.FLOTA_INTACTA:
            # Verificar si impactó alguna parte de la flota
            if coordenada in self.ship_cells:
                # Marcar impacto
                self.impactos[coordenada] = 'X'
                # Remover la celda ocupada
                self.ship_cells.discard(coordenada)
                # También quitar de la estructura de ships
                for t, sset in self.ships.items():
                    if coordenada in sset:
                        sset.discard(coordenada)
                        break

                # Si ya no quedan casillas con barcos, toda la flota está hundida
                if not self.ship_cells:
                    self.estado_actual = self.HUNDIDO
                    return "200", "Hundido"
                else:
                    return "200", "Impacto"
            else:
                self.impactos[coordenada] = 'O'  # Marcar fallo (agua)
                return "404", "Fallido"

        elif self.estado_actual == self.HUNDIDO:
            # Ya no hay barcos para hundir
            self.impactos[coordenada] = 'O'  # Marcar como agua
            return "404", "Flota_Ya_Hundida"
        
        # Estado no reconocido (no debería ocurrir, pero por completitud)
        return "500", "Error en el estado del autómata"
    
    def iniciar_servidor(self):
        """
        Inicia el servidor para escuchar ataques.
        """
        # Crear socket del servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Enlazar socket al host:puerto y escuchar conexiones
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)  # Escuchar solo una conexión a la vez
            
            print(f"\n╔══════════════════════════════════════════╗")
            print(f"║ [ SERVIDOR DE DEFENSA - FSM ]             ║")
            print(f"╚══════════════════════════════════════════╝")
            print(f"Escuchando en {self.host}:{self.port}...")
            
            # Mostrar estado inicial del tablero
            self.mostrar_tablero()
            
            while True:
                # Aceptar conexión del cliente
                client_socket, client_address = self.server_socket.accept()
                print(f"\nConexión establecida con {client_address}")
                
                try:
                    # Recibir ataque
                    data = client_socket.recv(1024).decode().strip()
                    print(f"Ataque recibido: {data}")
                    
                    # Procesar el ataque a través del FSM
                    codigo, respuesta = self.procesar_ataque(data)
                    
                    # Enviar respuesta
                    client_socket.send(f"{codigo}:{respuesta}".encode())
                    print(f"Respuesta enviada: {codigo}:{respuesta}")
                    
                    # Mostrar el tablero actualizado
                    self.mostrar_tablero()
                    
                    # Si el barco está hundido, mostrar mensaje de fin
                    if self.estado_actual == self.HUNDIDO:
                        print("\n¡El Destroyer ha sido hundido! Toda la flota destruida.")
                    
                except Exception as e:
                    print(f"Error al procesar la solicitud: {e}")
                
                finally:
                    # Cerrar la conexión con el cliente
                    client_socket.close()
        
        except KeyboardInterrupt:
            print("\nServidor detenido por el usuario.")
        except Exception as e:
            print(f"Error en el servidor: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            print("Servidor cerrado.")

def main():
    """
    Función principal para iniciar el servidor FSM.
    """
    servidor = NavalServerFSM()
    
    # Configuración inicial
    print("╔══════════════════════════════════════════╗")
    print("║ [ SERVIDOR DE DEFENSA - FSM ]             ║")
    print("╚══════════════════════════════════════════╝")
    print("🛠 Configuración inicial:")
    
    # Para este ejemplo didáctico, seleccionamos una posición fija
    # En una implementación completa, se pediría al usuario que la ingrese
    
    
    servidor.iniciar_servidor()
    # Iniciar servidor para recibir ataques
    

if __name__ == "__main__":
    main()
