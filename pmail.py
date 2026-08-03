#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-Mail: A simple POP3 mail server
Created on Mon Aug  3 10:04:53 2026

@author: Christoforos Prasatzakis
"""

import threading
import socket

#Handle incoming POP3 commands
def handle(data, conn):
    conn.sendall(b'+OK GEIA\r\n')

#Main connection loop
def connloop(conn):
    #Send a welcome message.
    conn.sendall(b'+OK Welcome\r\n')
    
    #Receive data.
    data = conn.recv(512)
        
    #On the QUIT command, stop the loop.
    while (b'QUIT\r\n' not in data):
        print(data)
        
        #Handle incoming data and receive new ones.
        handle(data, conn)
        
        data = conn.recv(512)
            
    #Once the loop is over, close connection.
    conn.close()

#Main function        
def main():
    #Prepare the socket
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.bind(('',110))
    my_socket.listen()
    
    while (True):
        #Accept incoming connections and initiate connection loops.
        conn, addr = my_socket.accept()
        
        thread = threading.Thread(target=connloop, args=(conn,))
        
        thread.start()
        
main()