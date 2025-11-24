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
        # Valores posibles: None (agua), 'D' (Destroyer)
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
        
        # Socket del servidor
        self.server_socket = None
        self.host = '192.168.10.187' ##'localhost'  # Para propósitos educativos, usar localhost
        self.port = 5000         # Puerto por defecto
    
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
        
        # Colocar el Destroyer
        self.tablero[posicion_destroyer] = 'D'
        
        # Cambiar estado a FLOTA_INTACTA
        self.estado_actual = self.FLOTA_INTACTA
        print(f"Destroyer colocado en {posicion_destroyer}")
        return True
    
    def mostrar_tablero(self):
        """
        Muestra el tablero actual del juego.
        """
        print("\nTablero de defensa (5x5):")
        print("  1 2 3 4 5")
        print(" ┌─────────┐")
        
        for fila in ['A', 'B', 'C', 'D', 'E']:
            print(f"{fila}│", end="")
            for col in ['1', '2', '3', '4', '5']:
                pos = f"{fila}{col}"
                if self.impactos[pos] == 'X':
                    print("X ", end="")  # Impacto
                elif self.impactos[pos] == 'O':
                    print("O ", end="")  # Agua
                elif self.tablero[pos] == 'D':
                    print("D ", end="")  # Destroyer (visible solo para el servidor)
                else:
                    print("~ ", end="")  # Agua sin atacar
            print("│")
        
        print(" └───┘")
        print(" D: Destroyer, ~: Agua, O: Fallo, X: Impacto")
        
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
            # Verificar si impactó el Destroyer
            if self.tablero[coordenada] == 'D':
                self.impactos[coordenada] = 'X'  # Marcar impacto
                self.estado_actual = self.HUNDIDO  # Transición al estado HUNDIDO
                return "200", "Hundido"
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
