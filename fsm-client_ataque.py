"""
FSM Naval Battle - Cliente de Ataque
-----------------------------------
Este programa implementa un cliente que envía ataques (cadenas de entrada)
al servidor de defensa y muestra los resultados en una cuadrícula 5x5.

Autómata Finito para el Cliente:
-------------------------------
Q = {q0, q1, q2, q3} : {Inicio, Atacando, Victoria, Derrota}
Σ = {Hit, Miss, Sunk, Error}
q₀ = q0 (Inicio)
F = {q2, q3} (Victoria o Derrota - Estados finales)
"""

import socket
import time

class NavalClientFSM:
    """
    Implementación de la Máquina de Estados Finitos para el cliente de ataque naval.
    """
    # Estados del autómata
    INICIO = 'q0'      # Estado inicial
    ATACANDO = 'q1'    # En proceso de ataque
    VICTORIA = 'q2'    # Toda la flota enemiga ha sido hundida
    DERROTA = 'q3'     # No se logró hundir la flota enemiga
    
    def __init__(self):
        # Estado actual del autómata
        self.estado_actual = self.INICIO
        
        # Tablero de seguimiento de ataques (5x5)
        # Valores: '~' (sin atacar), 'O' (fallo/agua), 'X' (impacto)
        self.filas = ['A', 'B', 'C', 'D', 'E']
        self.columnas = ['1', '2', '3', '4', '5']
        # Generar posiciones A1..E5
        self.tablero_ataques = {f"{f}{c}": '~' for f in self.filas for c in self.columnas}
        
        # Conexión con el servidor
        self.server_host = 'localhost'  # Por defecto localhost para facilidad
        self.server_port = 5000         # Puerto por defecto
        
        # Contador de ataques
        self.ataques_realizados = 0
        self.barcos_hundidos = 0
        
    def mostrar_tablero(self):
        """
        Muestra el tablero de ataques realizados.
        """
        cols = self.columnas
        filas = self.filas

        print(f"\nTablero de ataque ({len(filas)}x{len(cols)}):")
        # Imprimir cabeceras de columna
        print("  " + " ".join(cols))

        # Construir líneas de borde según ancho
        inner_width = len(cols) * 2  # cada celda usa 2 caracteres (símbolo + espacio)
        print(" " + "┌" + "─" * inner_width + "┐")

        for fila in filas:
            print(f"{fila}│", end="")
            for col in cols:
                pos = f"{fila}{col}"
                if self.tablero_ataques[pos] == 'X':
                    print("X ", end="")  # Impacto
                elif self.tablero_ataques[pos] == 'O':
                    print("O ", end="")  # Agua
                else:
                    print("~ ", end="")  # Sin atacar
            print("│")

        print(" " + "└" + "─" * inner_width + "┘")
        print(" ~: Sin atacar, O: Fallo, X: Impacto")
    
    def enviar_ataque(self, coordenada):
        """
        Envía un ataque al servidor y procesa la respuesta según la FSM.
        
        Args:
            coordenada: Coordenada del ataque (ej: 'A1')
            
        Returns:
            Respuesta del servidor
        """
        try:
            # Validar coordenada
            if coordenada not in self.tablero_ataques:
                valids = ", ".join(sorted(self.tablero_ataques.keys()))
                print(f"Coordenada {coordenada} inválida. Usa una de: {valids}.")
                return None
                
            # Crear socket para conectar al servidor
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.server_host, self.server_port))
            
            # Enviar coordenada
            client_socket.send(coordenada.encode())
            
            # Recibir respuesta
            response = client_socket.recv(1024).decode()
            
            # Cerrar socket
            client_socket.close()
            
            # Incrementar contador de ataques
            self.ataques_realizados += 1
            
            # Procesar respuesta según FSM
            self._procesar_respuesta(coordenada, response)
            
            return response
            
        except ConnectionRefusedError:
            print(f"Error: No se pudo conectar al servidor en {self.server_host}:{self.server_port}")
            return None
        except Exception as e:
            print(f"Error al enviar el ataque: {e}")
            return None
    
    def _procesar_respuesta(self, coordenada, respuesta):
        """
        Procesa la respuesta del servidor y actualiza el estado del FSM.
        
        Args:
            coordenada: Coordenada atacada
            respuesta: Respuesta del servidor
        """
        codigo, mensaje = respuesta.split(':', 1)
        
        # Función de transición δ según el estado actual y la entrada
        if self.estado_actual == self.INICIO:
            # Transición al estado ATACANDO
            self.estado_actual = self.ATACANDO
        
        if self.estado_actual == self.ATACANDO:
            if codigo == "200" and "Hundido" in mensaje:
                # Barco impactado y hundido
                self.tablero_ataques[coordenada] = 'X'
                self.barcos_hundidos += 1
                
                # Si hundir todos los barcos era el objetivo final, transición a VICTORIA
                self.estado_actual = self.VICTORIA
                
            elif codigo == "202" and "Impactado" in mensaje:
                # Barco impactado pero no hundido
                self.tablero_ataques[coordenada] = 'X'
                
            elif codigo == "404" and "Fallido" in mensaje:
                # Fallo (agua)
                self.tablero_ataques[coordenada] = 'O'
                
            elif "409" in codigo:
                # Ataque repetido
                print(f"Error: {mensaje} - Coordenada ya atacada")
                self.ataques_realizados -= 1  # No contar como ataque válido
                
            elif "404" in codigo and coordenada not in self.tablero_ataques:
                # Error en la coordenada
                print(f"Error: {mensaje}")
                self.ataques_realizados -= 1  # No contar como ataque válido
        
        # Para este juego simplificado, no implementamos transición a DERROTA
        # ya que se puede seguir atacando hasta hundir el barco
    
    def iniciar_cliente(self):
        """
        Inicia el cliente de ataque.
        """
        print("\n╔══════════════════════════════════════════╗")
        print("║ [ CLIENTE DE ATAQUE - FSM ]              ║")
        print("╚══════════════════════════════════════════╝")
        
        # Configurar conexión al servidor
        print(f"Ingrese la IP del servidor (Enter para usar {self.server_host}):")
        host = input()
        if host:
            self.server_host = host
            
        print(f"Ingrese el puerto del servidor (Enter para usar {self.server_port}):")
        port = input()
        if port:
            self.server_port = int(port)
        
        print(f"\nConectando al servidor en {self.server_host}:{self.server_port}")
        
        # Mostrar tablero inicial
        self.mostrar_tablero()
        
        # Bucle principal de juego
        while self.estado_actual != self.VICTORIA and self.estado_actual != self.DERROTA:
            print("\nIngrese coordenada de ataque (ej: B1):")
            coordenada = input().strip().upper()
            
            if not coordenada:
                continue
            
            # Enviar ataque y recibir respuesta
            respuesta = self.enviar_ataque(coordenada)
            
            if respuesta:
                print(f"Respuesta: {respuesta}")
                
                # Mostrar tablero actualizado
                self.mostrar_tablero()
                
                # Verificar si se ha ganado
                if self.estado_actual == self.VICTORIA:
                    print("\n¡Has ganado! Toda la flota enemiga ha sido destruida.")
                    print(f"Ataques realizados: {self.ataques_realizados}")
                    break
        
        print("\nFin del juego.")

def main():
    """
    Función principal para iniciar el cliente FSM.
    """
    cliente = NavalClientFSM()
    cliente.iniciar_cliente()

if __name__ == "__main__":
    main()
