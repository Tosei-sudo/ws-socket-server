
import SocketServer
import base64
import hashlib
from BaseHTTPServer import BaseHTTPRequestHandler
import mimetools
import select
import threading

def build_ws_msg(payload):
    byte1 = 0x81
    byte2 = 0x00 + len(bytes(payload))

    ws_msg = bytearray()
    ws_msg.append(byte1)
    ws_msg.append(byte2)

    for byte in bytes(payload):
        ws_msg.append(byte)
    return ws_msg

class WsServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    
    def __init__(self, server_address, RequestHandlerClass):
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False
        
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        
        self.ws_sockets = []
        self.sequence = [self.socket]
    
    def serve_forever(self, poll_interval=0.5):
        self.__is_shut_down.clear()
        try:
            
            while not self.__shutdown_request:
                
                r, w, e = select.select(self.sequence, [], [], poll_interval)
                print len(self.sequence)
                for sock in r:
                    if sock.fileno() == -1:
                        continue
                    if sock == self.socket:
                        self._handle_request_noblock()
                    elif sock in self.ws_sockets:
                        print "WS"
                    else:
                        self._handle_request_noblock()
                self.check_ws_clients()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        self.__shutdown_request = True
        self.__is_shut_down.wait()
    
    def check_ws_clients(self):
        for ws_socket in self.ws_sockets:
            try:
                print ws_socket.fileno()
                # if received data from ws_socket then print data
                data = ws_sokect.recv(1024)
                print data
                
                ws_socket.send(build_ws_msg("Hello World"))
            except:
                self.ws_sockets.remove(ws_socket)
                self.sequence.remove(ws_socket)

class WsServerHandler(SocketServer.StreamRequestHandler):
    MessageClass = mimetools.Message
    
    def __init__(self, request, client_address, server):
        self.close_connection = 1
        SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)
    
    def build_http_response(self, status_code, headers, body):
        status_msg = BaseHTTPRequestHandler.responses.get(status_code, ["Error"])[0]
        response = "HTTP/1.1 " + str(status_code) + " " + status_msg + "\r\n"
        
        extend_headers = self.get_default_headers()
        extend_headers.update(headers)
        
        for header in extend_headers:
            response += header + ": " + extend_headers[header] + "\r\n"
        response += "\r\n" + body
        return response
    
    def get_default_headers(self):
        return {
            "Content-Type": "text/html",
            "Connection": "close",
            "Server": "WsServer",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        }
    
    def is_ws_handshake(self):
        return self.raw_request_liine.startswith("GET") and self.headers.get("Upgrade") == "websocket"

    def handshake_response(self):
        key = self.headers.get("Sec-WebSocket-Key")
        response_key = base64.b64encode(hashlib.sha1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
        headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Accept": response_key
        }
        return self.build_http_response(101, headers, "")
    
    def parse_request(self):
        try:
            self.headers = self.MessageClass(self.rfile, 0)
            return True
        except ValueError:
            return None
    
    def handle_one_request(self):
        self.raw_request_liine = self.rfile.readline(65537)
        
        if not self.parse_request():
            # An error code has been sent, just exit
            return
        if self.is_ws_handshake():
            # ws handshake
            # append client to ws_clients
            self.server.ws_sockets.append(self.connection)
            self.server.sequence.append(self.connection)
            # return handshake response
            self.wfile.write(self.handshake_response())
            self.close_connection = 0
        else:
            self.wfile.write(self.build_http_response(200, {}, "Hello World"))
            
    def handle(self):
        self.close_connection = 1
        print "Client connected"
        
        self.handle_one_request()
        while not self.close_connection:
            self.handle_one_request()

if __name__ == "__main__":
    server = WsServer(("127.0.0.1", 9999), WsServerHandler)
    server.serve_forever()