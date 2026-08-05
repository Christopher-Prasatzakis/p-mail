#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 14:49:29 2026

@author: Christoforos Prasatzakis
"""

import threading
import socket
import json
from hashlib import sha256
import datetime

#Enable logging?
logging = True

#Print log messages on screen as well?
prtscrn = True

#Max data size in octets.
dlimit = 10485760

#User list.
users = None

#Recipient list per session.
recipients = {}

#Senders per session.
senders = {}

#Data buffers per session.
databuf = {}

#Write a message to the log file
def log(message):
    if (not logging):
        return
    
    fn = datetime.datetime.now().strftime('logfile-%Y%m%d.log')
    logfile = open(f'logs/smtp/{fn}', 'a')
    date = datetime.datetime.now().strftime('[%Y-%m-%d %H:%M:%S]: ')
    logfile.write(f'{date}{message}\r\n')
    
    if (prtscrn):
        print(f'{date}{message}')
    
    logfile.close()

#Load the user list from JSON.
def loadusers():
    global users
    
    f = open('userlist.json', 'r')
    users = json.load(f)
    f.close()
    
#Get the max ID according to metadata.
def maxid(metadata):
    if (metadata == {}):
        return 1
    
    mid = -1
    
    for fn in metadata:
        if (metadata[fn]['id'] > mid):
            mid = metadata[fn]['id']
            
    return (mid + 1)
    
#Send a message to a recipient.
def send(data, octets, recipient):
    #First, we need to prepare the message metadata.
    metadata = {}
    log('Sending data')
    
    total = b''.join(data)
        
    sha = sha256(total).hexdigest()[:8]
    
    filename = f'{sha}.eml'
    uid = sha
    date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    f = open(f'mail/{recipient}/metadata.json', 'r')
    rcpdata = json.load(f)
    f.close()
    
    metadata['id'] = maxid(rcpdata)
    metadata['uid'] = uid
    metadata['received'] = date
    metadata['size'] = octets
    metadata['delete'] = 0
    
    #Now, we need to add the metadata to the recipient's metadata file.
    rcpdata[filename] = metadata
    f = open(f'mail/{recipient}/metadata.json', 'w')
    json.dump(rcpdata, f)
    f.close()
    
    #And then, save the message itself.
    f = open(f'mail/{recipient}/messages/{filename}', 'w')
    
    for s in data:
        f.write(s.decode())
        
    f.close()
    log('Data sent')
    
#Function for entering data.
def dataentry(conn, session):
    global dlimit
    
    octets = 0
    
    data = conn.recv(dlimit)
    log(data)
    
    while (True):
        octets += len(data)
        databuf[session].append(data)
        data = conn.recv(dlimit)
        log(data)
        
        if ((b'\r\n.\r\n' in data) or (data.decode().strip('\r\n') == '.')):
            octets += len(data) - 3
            databuf[session].append(data[:len(data) - 3])
            break
        
    for r in recipients[session]:
        send(databuf[session], octets, r)

#Command functions follow.
def helo(data, conn, session):
    arg = data.decode().strip('HELO ')
    conn.sendall(f'250 Hello {arg}'.encode())
    
def ehlo(data, conn, session):
    global dlimit
    #arg = data.decode().strip('EHLO ')
    hostname = socket.gethostname()
    conn.sendall(f'250-{hostname}\r\n'.encode())
    conn.sendall(b'250-PIPELINING\r\n')
    conn.sendall(b'250-8BITMIME\r\n')
    conn.sendall(f'250-SIZE {dlimit}\r\n'.encode())
    conn.sendall(b'250 HELP\r\n')
    
def noop(data, conn, session):
    conn.sendall(b'250 OK\r\n')
    
def mail(data, conn, session):
    user = data.decode().strip('MAIL FROM:').strip('<>').strip(' ').rstrip('\r\n')
    user = user[:user.index('@')]
    
    userfound = False
    
    for u in users:
        if (u["username"] == user):
            userfound = True
            
    if (not userfound):
        conn.sendall(b'550 Invalid sender\r\n')
        return
    
    senders[session] = user
    
    conn.sendall(b'250 OK\r\n')
    
def rcpt(data, conn, session):
    user = data.decode().strip('RCPT TO:').strip('<>').strip(' ').rstrip('\r\n')
    user = user[:user.index('@')]
    
    userfound = False
    
    for u in users:
        if (u["username"] == user):
            userfound = True
            
    if (not userfound):
        conn.sendall(b'550 Invalid recipient\r\n')
        return
    
    recipients[session].append(user)
    
    conn.sendall(b'250 OK\r\n')
    
def rset(data, conn, session):
    senders.pop(session)
    databuf[session] = []
    recipients[session] = []
    
    conn.sendall(b'250 OK\r\n')
    
def vrfy(data, conn, session):
    arg = data.decode().strip('VRFY ').rstrip('\r\n')
    
    userfound = False
    
    for u in users:
        if (u["username"] == arg):
            userfound = True
            
    if (not userfound):
        conn.sendall(b'550 Unknown user\r\n')
        return
    
    conn.sendall(b'250 OK\r\n')
    
def dat(data, conn, session):
    conn.sendall(b'354 End data with <CRLF>.<CRLF>\r\n')
    dataentry(conn, session)
    conn.sendall(b'250 OK\r\n')
    
#Command-function map.
funcs = {'HELO':helo, 'EHLO':ehlo, 'NOOP':noop, 'MAIL':mail, 'RCPT':rcpt, 'RSET':rset, 'VRFY':vrfy, 'DATA':dat}

#Incoming command handler.
def handle(data, conn, session):
    command = data.decode().split(' ')[0].rstrip('\r\n')
    
    if (command not in funcs.keys()):
        conn.sendall(b'500 Unknown command\r\n')
        return
    
    funcs[command](data, conn, session)
    
#Thread loop function.
def threadloop(conn, session):
    #Send a welcome message.
    hostname = socket.gethostname()
    conn.sendall(f'220 {hostname} ESMTP ready\r\n'.encode())
    
    recipients[session] = []
    databuf[session] = []
    
    #Receive data.
    data = conn.recv(512)
        
    #On the QUIT command, stop the loop.
    while (b'QUIT\r\n' not in data):
        log(data)
        
        #Handle incoming data and receive new ones.
        handle(data, conn, session)
        
        data = conn.recv(512)
            
    #Once the loop is over, close connection.
    conn.sendall(b'221 Goodbye\r\n')
    conn.close()
    recipients.pop(session)
    log(f'Session {session} over.')

#Main function        
def main():
    #Load the port
    f = open('port.txt', 'r')
    f.readline()
    port = int(f.readline())
    f.close()

    #Load users
    loadusers()
    
    #Prepare the socket
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.bind(('',port))
    my_socket.listen()
    
    sid = 0

    log(f'P-Mail SMTP Server up and running at port {port}.')
    
    while (True):
        #Accept incoming connections and initiate connection loops.
        conn, addr = my_socket.accept()

        log("Connection Accepted")

        thread = threading.Thread(target=threadloop, args=(conn,sid))
        
        thread.start()
        
        sid += 1
        
main()
