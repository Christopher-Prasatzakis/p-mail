#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 10:36:51 2026

@author: Christoforos Prasatzakis
"""

import threading
import socket
import json
import os

#Object for managing user sessions
class Session:
    def __init__(self, sid):
        self.sid = sid
        self.username = None
        self.connected = False
        
#The user list.
users = None

#Metadata for each user.
metadata = {}

#The port where the server will be operating on.
port = 110

#Load metadata for a user.
def load_metadata(username):
    f = open(f'mail/{username}/metadata.json', 'r')
    md = json.load(f)
    f.close()
    metadata[username] = md

#Load the user list from JSON.
def loadusers():
    global users
    
    f = open('userlist.json', 'r')
    users = json.load(f)
    f.close()
       
#The following functions implement POP3 commands.
def quitit(data, conn, session, arg, arg2):
    return

def noop(data, conn, session, arg, arg2):
    conn.sendall(b'+OK\r\n')
    
def user(data, conn, session, arg, arg2):
    if (arg == None):
        conn.sendall(b'-ERR No username provided\r\n')
        return
    
    if (session.username != None):
        conn.sendall(b'-ERR Username already specified\r\n')
        return
    
    if (session.connected):
        conn.sendall(b'-ERR Already authenticated\r\n')
        return
    
    for u in users:
        if (u['username'] == arg):
            session.username = arg
            conn.sendall(b'+OK Username accepted\r\n')
            return
            
    conn.sendall(b'-ERR Invalid username\r\n')
    
def passw(data, conn, session, arg, arg2):
    if (arg == None):
        conn.sendall(b'-ERR No password given\r\n')
        return
    
    if (session.username == None):
        conn.sendall(b'-ERR No username given\r\n')
        return
    
    if (session.connected):
        conn.sendall(b'-ERR Already authenticated\r\n')
        return
    
    #if(session.username not in users.keys()):
        #conn.sendall(b'-ERR Authentication failed\r\n')
        #return
    
    for u in users:
        if (u['username'] == session.username):
            if (u['password'] == arg):
                if (os.path.isfile(f'mail/{session.username}/{session.username}.lock')):
                    conn.sendall(b'-ERR Mailbox already locked!\r\n')
                    return
                
                f = open(f'mail/{session.username}/{session.username}.lock', 'w')
                f.close()
                conn.sendall(b'+OK Mailbox locked\r\n')
                load_metadata(session.username)
                session.connected = True
                return
                
    conn.sendall(b'-ERR Authentication failed\r\n')
    
def retr(data, conn, session, arg, arg2):
    if (arg == None):
        conn.sendall(b'-ERR No message ID provided\r\n')
        return
    
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    for m in metadata[session.username]:
        if (metadata[session.username][m]['id'] == int(arg)):
            conn.sendall(f'+OK {metadata[session.username][m]["size"]} octets\r\n'.encode())
            
            f = open(f'mail/{session.username}/messages/{m}', 'r')
            l = f.readline()
            
            while (l != ''):
                conn.sendall((l.rstrip('\r\n') + '\r\n').encode())
                l = f.readline()
                
            f.close()
            conn.sendall(b'.\r\n')
            
            return
        
    conn.sendall(b'-ERR No such message\r\n')
    
def stat(data, conn, session, arg, arg2):
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    messages = len(metadata[session.username])
    octets = 0
    
    for m in metadata[session.username]:
        octets += metadata[session.username][m]["size"]
        
    s = f'+OK {messages} {octets}\r\n'
    conn.sendall(s.encode())
    
def lst(data, conn, session, arg, arg2):
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    messages = len(metadata[session.username])
    
    if (arg == None):
        conn.sendall(f'+OK {messages} messages\r\n'.encode())
    
        for m in metadata[session.username]:
            s = f'{metadata[session.username][m]["id"]} {metadata[session.username][m]["size"]}\r\n'
            conn.sendall(s.encode())
            
        conn.sendall(b'.\r\n')
    else:
        for m in metadata[session.username]:
            if (metadata[session.username][m]["id"] == int(arg)):
                s = f'+OK {metadata[session.username][m]["id"]}  {metadata[session.username][m]["size"]}\r\n'
                conn.sendall(s.encode())
                return
            
        conn.sendall(b'-ERR No such message\r\n')
        
def dele(data, conn, session, arg, arg2):
    if (arg == None):
        conn.sendall(b'-ERR No message ID provided\r\n')
        return
    
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    for m in metadata[session.username]:
        if (metadata[session.username][m]["id"] == int(arg)):
            metadata[session.username][m]["delete"] = 1
            conn.sendall(b'+OK Message marked for deletion\r\n')
            return
        
    conn.sendall(b'-ERR No such message\r\n')
    
def rset(data, conn, session, arg, arg2):
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    restored = 0
    
    for m in metadata[session.username]:
        if (metadata[session.username][m]["delete"] == 1):
            metadata[session.username][m]["delete"] = 0
            restored += 1
            
    conn.sendall(f'+OK {restored} messages restored\r\n'.encode())
    
def uidl(data, conn, session, arg, arg2):
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    conn.sendall(b'+OK\r\n')
    
    for m in metadata[session.username]:
        i = metadata[session.username][m]["id"]
        ui = metadata[session.username][m]["uid"]
        
        conn.sendall(f'{i} {ui}\r\n'.encode())
        
    conn.sendall(b'.\r\n')
    
def top(data, conn, session, arg, arg2):
    if (session.connected != True):
        conn.sendall(b'-ERR Not authenticated\r\n')
        return
    
    if (arg == None):
        conn.sendall(b'-ERR No message ID given\r\n')
        return
    
    if (arg2 == None):
        conn.sendall(b'-ERR No number of lines provided\r\n')
        return
    
    fname = None
    
    for m in metadata[session.username]:
        if (int(arg) == metadata[session.username][m]["id"]):
            fname = m
            
    if (fname == None):
        conn.sendall(b'-ERR No such message\r\n')
        return
    
    f = open(f'mail/{session.username}/messages/{m}', 'r')
    
    l = f.readline()
    
    while ((l != '\n') and (l != '\r\n')):
        conn.sendall((l.rstrip('\r\n') + '\r\n').encode())
        l = f.readline()
        
    conn.sendall(b'\r\n')
    
    for i in range(0, int(arg2)):
        l = f.readline()
        
        if (l == ''):
            break
        
        conn.sendall((l.rstrip('\r\n') + '\r\n').encode())
        
    conn.sendall(b'.\r\n')

def capa(data, conn, session, arg, arg2):
    conn.sendall(b'+OK Capability list follows\r\nUSER\r\nUIDL\r\nTOP\r\n.\r\n')

#Command-function map.
funcs = {'QUIT':quitit, 'NOOP':noop, 'USER':user, 'PASS':passw, 'RETR':retr, 'STAT':stat, 'LIST':lst, 'DELE':dele, 'RSET':rset, 'UIDL':uidl, 'TOP':top, 'CAPA':capa}
        
#Dispatcher function for input commands.
def handle(data, conn, session):
    c = data.decode().split(' ')
    command = None
    arg = None
    arg2 = None
    
    if (len(c) == 2):
        command = c[0].rstrip('\r\n')
        arg = c[1].rstrip('\r\n')
    elif (len(c) == 3):
        command = c[0].rstrip('\r\n')
        arg = c[1].rstrip('\r\n')
        arg2 = c[2].rstrip('\r\n')
    else:
        command = c[0].rstrip('\r\n')
        
    if (command not in funcs.keys()):
        conn.sendall(b'-ERR Invalid command\r\n')
    else:
        funcs[command](data, conn, session, arg, arg2)
        
#Clean up the user's mailbox on session close.
def cleanup(session):
    nodelete = {}
    for m in metadata[session.username]:
        if (metadata[session.username][m]["delete"]):
            os.remove(f'mail/{session.username}/messages/{m}')
        else:
            nodelete[m] = metadata[session.username][m]
            
    f = open(f'mail/{session.username}/metadata.json', 'w')
    json.dump(nodelete, f)
    f.close()
        
#Thread loop function.
def threadloop(conn, session):
    #Send a welcome message.
    conn.sendall(b'+OK Welcome\r\n')
    
    #Receive data.
    data = conn.recv(512)
        
    #On the QUIT command, stop the loop.
    while (b'QUIT\r\n' not in data):
        print(data)
        
        #Handle incoming data and receive new ones.
        handle(data, conn, session)
        
        data = conn.recv(512)
            
    #Once the loop is over, close connection.
    conn.sendall(b'+OK Goodbye!\r\n')
    
    if (session.username != None):
        cleanup(session)
        os.remove(f'mail/{session.username}/{session.username}.lock')
        session.username = None
        session.connected = False
        
    conn.close()
    print(f'Session {session.sid} over.')

#Main function        
def main():
    global port

    #Load users
    loadusers()
    
    #Prepare the socket
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.bind(('',port))
    my_socket.listen()
    
    sid = 0

    print(f'P-Mail POP3 Server up and running at port {port}.')
    
    while (True):
        #Accept incoming connections and initiate connection loops.
        conn, addr = my_socket.accept()
        
        thread = threading.Thread(target=threadloop, args=(conn,Session(sid)))
        
        thread.start()
        
        sid += 1
        
main()
