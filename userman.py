#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  5 07:15:15 2026

@author: Christoforos Prasatzakis
"""

import json
import os

#Is the program running?
running = True

#The user list
users = None

#Import user list
def loadusers():
    global users
    
    f = open('userlist.json', 'r')
    users = json.load(f)
    f.close()
    
#Save user list
def saveusers():
    global users
    
    f = open('userlist.json', 'w')
    json.dump(users, f)
    f.close()
    
#Add a new user
def adduser():
    global users
    
    username = input('New username: ')
    password = input('New password: ')
    
    users.append({"username":username, "password":password})
    
    os.mkdir(f'mail/{username}')
    os.mkdir(f'mail/{username}/messages')
    
    f = open(f'mail/{username}/metadata.json', 'w')
    f.write('{}')
    f.close()
    
#Delete a user
def deluser():
    global users
    
    username = input('Username: ')
    
    nodelete = []
    deleted = False
    
    for u in users:
        if (u['username'] != username):
            nodelete.append(u)
        else:
            deleted = True
            
    users = nodelete
    
    if (deleted == False):
        print(f'ERROR: User {username} not found!')
    else:
        os.system(f'rm -rf mail/{username}')
        
#Change a user's password
def changepass():
    global users
    
    username = input('Username: ')
    newpass = input(f'New password for user {username}: ')
    
    for u in users:
        if (u['username'] == username):
            u['password'] = newpass
            return
        
    print(f'ERROR: User {username} not found!')
    
#List all users.
def listusers():
    if (users == []):
        print('No users')
        
    print('USERNAME\tPASSWORD')
    
    for u in users:
        print(f'{u["username"]}\t{u["password"]}')
        
#Exit the program
def qu():
    global running
    
    running = False
    
    print('Goodbye!')
    
#Dispatch user input
def dispatch(inp):
    funcs = [adduser, deluser, changepass, listusers, qu]
    
    if not ((inp >= 1) and (inp <= 5)):
        print('ERROR: Invalid choice')
        return
    
    funcs[inp - 1]()
    
def menu():
    while (running):
        print('')
        print('P-Mail User Manager')
        print('===================')
        print('')
        print('1. Add a new user')
        print('2. Delete an existing user')
        print('3. Change a user password')
        print('4. List all users')
        print('5. Quit')
        print('')
        choice = int(input('Enter your choice [1 - 5]: '))
        print('')
        dispatch(choice)
        
def main():
    loadusers()
    menu()
    saveusers()
    
main()