import socket
import os
import sys
import select
import threading
import errno
from Cryptodome.Cipher import DES

class Server():
    def __init__(self):
        self.host = '' 
        self.backlog = 5 
        self.size = 1024 
        self.server = None
        self.threads = [] 
        self.port = ''
        self.checkPortAndPath()
        
    def checkPortAndPath(self):
        if not len(sys.argv) == 3:
            print("Please specify the server directory for storing and retrieving files and the port.")
            os._exit(1)
        try:
            self.port = int(sys.argv[2])
        except:
            print("Please specify port as an integer value.")
            os._exit(1)
        
    def checkConf(self):
        return os.path.exists("./dfs.conf")

    # Open a socket and bind the port number to listen for incoming connections.
    def openSocket(self): 
        try: 
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port)) 
            self.server.listen(5) 
            print("The webserver has started. Listening on port " + str(self.port) + "...")
        except Exception as errors:
            if self.server: 
                self.server.close() 
            print ("Could not open socket: " + errors) 
            os._exit(1) 

    def run(self): 
        try:
            if not self.checkConf():
                raise FileNotFoundError
            self.openSocket() 
            running = 1
            inputSock = [self.server]
            while running: 
                inputready, outputready, exceptready = select.select(inputSock, [], [])
                for s in inputready:                
                    # handle the server socket 
                    c = Client(self.server.accept())
                    # if a client connection is established, serve the requests in a new thread
                    c.start()
                    self.threads.append(c)
                    for t in self.threads:
                        if hasattr(t, "stopped"):
                            t.join()
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
            os._exit(1)
        except FileNotFoundError:
            print("dfs.conf file was not found.")
            os._exit(1)
        except Exception as err:
            # close all threads 
            print("Closing server")
            print("Error - ", err)
            self.server.close() 
            for c in self.threads: 
                c.join()
            os._exit(1)

class Client(threading.Thread):
    def __init__(self, clientAddr):
        (client, address) = clientAddr
        threading.Thread.__init__(self, name=address)
        self.client = client 
        self.clientAddr = address 
        self.size = 1024
        self.users = {}
        self.user = ''
        self.password = ''
        self.filePath = ''
        self.key = 'datacomm'
        self.des = DES.new(self.key.encode(), DES.MODE_ECB)
        self.getUsers()
        self.setFilePath()
        
    def setFilePath(self):
        self.filePath = sys.argv[1]
        self.filePath = self.filePath.replace("\\", "/")            
        if not self.filePath.startswith("./"):
            self.filePath = "./" + self.filePath
        if not (self.filePath.startswith(".")):
            self.filePath = "." + self.filePath
        if not self.filePath.endswith("/"):
            self.filePath = self.filePath + "/"

    def run(self):
        try:
            request = self.des.decrypt(self.client.recv(self.size)).strip()
            if not request:
                self.client.close()
                sys.exit()
            print(request.decode())
            command, self.user, self.password = request.decode().split('|*|*|')
            self.authenticateUser()
            self.checkCommand(command)
        except FileNotFoundError as err:
            print("Error - ", err)
            self.client.close()
            sys.exit()

    def authenticateUser(self):
        if self.user in self.users.keys():
            if not self.password == self.users[self.user]:
                self.sendFile("Authentication failed", True)
                self.client.close()
                sys.exit()
        else:
            self.sendFile("Authentication failed", True)
            self.client.close()
            sys.exit()        
        self.sendFile("Authenticated", True)

    def checkCommand(self, command):
        method = command.split()
        if(method[0] == "put"):
            fileName = method[1]
            self.put(fileName)
        elif(method[0] == "getl"):
            fileName = method[1]
            self.getLFile(fileName)
        elif(method[0] == "get"):
            fileName = method[1]
            self.getFile(fileName)
        elif(method[0] == "list"):
            try:
                fileName = method[1]
            except:
                fileName = "."
            self.listFiles(fileName)
    
    def getFile(self, fileName):
        filePath = self.filePath + self.user + "/" + fileName
        chunkSize = str(os.path.getsize(filePath) + 100)
        #send the read/write chunk size before sending the file
        self.sendFile(chunkSize, True)
        with open(filePath, 'rb') as fh:
            self.sendFile(fh.read(), False)
            fh.close()
        
    def generateFileNameForGet(self, fileName):
        if fileName.startswith("."):
            fileName = fileName[2:]
        path = fileName.split("/")
        path.pop()
        path = self.filePath + '/'.join(path)
        fileName = fileName.split("/")[-1] + "."
#         filePath = path + "/" + fileName
        return path, fileName
        
    def getLFile(self, fileName):
        filePath, fileName = self.generateFileNameForGet(fileName)        
        files = []
        for file in os.listdir(path=filePath):
            if file[:-1] == fileName:
                file = filePath + "/" + file
                files.append(file)
        files = '|*|*|'.join(files)
        if len(files) == 0:
            files = 'File not found'
            print(files)
        self.sendFile(files, True)

    def listFiles(self, fileName):
        listOfFiles = self.getListOfFiles(fileName)
        data = '|*|*|'.join(listOfFiles)
        self.sendFile(data, True)
        
    def getListOfFiles(self, fileName):
        if fileName.startswith("./"):
            fileName = fileName[1:]
        if not fileName.startswith("/"):
            fileName = "/" + fileName
        try:
            listFiles = []
            for root, subFolders, files in os.walk(self.filePath + self.user + fileName):
                for file in files:
                    rep = self.filePath[1:-1]
                    root = root.replace(rep, '')
                    path = root + "\\" + file
                    path = path.replace("\\", "/")
                    listFiles.append(path)
            if len(listFiles) == 0:
                raise FileNotFoundError
        except FileNotFoundError:
            print("Error - No files found")
            self.sendFile("no files found", True)
            self.client.close()
            sys.exit()
        except Exception as err:
            print("Error - ", err)
            self.client.close()
            sys.exit()
        return listFiles

    def put(self, fileName):
        i = 0
        request = []
        self.size = int(self.des.decrypt(self.client.recv(self.size)).decode().strip())
        while i < 2:
            i = i + 1
            data = self.putFile()
            request.append(data)
        if (len(request) == 0):
            return
        self.saveFile(fileName, request)

    def putFile(self):
        try:
            request = self.des.decrypt(self.client.recv(self.size)).strip()
        except ConnectionAbortedError as err:
            print ("Error - Connection aborted by client.\n", err)
            return
        except ConnectionResetError as err:
            print ("Error - Connection reset by client.\n", err)
            return
        except socket.timeout as err:
            print("Client connection timed out.")
            return
        except ValueError as err:
            print ("KeepaliveTime Value in the configuration file is not an integer or a float")
            return
        except socket.error as err:
            print ("Error - Socket Error.\n", err)
            return
        except Exception as err:
            print ("Error - Socket Error.\n", err)
            return
#         self.client.close()
        return request

    def saveFile(self, fileName, fileContents):
        if fileName.startswith("."):
            fileName = fileName[2:]
        path = fileName.split("/")
        path.pop()
        path = self.filePath + '/'.join(path)
        self.createDirs(path)
        chunkNo = int(fileName[-1])
        fileName = fileName.split("/")[-1][:-1]
        filePath = path + "/" + fileName
        for contents in fileContents:
            with open(filePath + str((chunkNo)), 'wb') as fh:
                fh.write(contents)
                fh.close()
                chunkNo += 1
                if chunkNo == 5:
                    chunkNo = 1

    def createDirs(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if (exc.errno == errno.EEXIST and os.path.isdir(path)):
                return

    def getUsers(self):
        with open("./dfs.conf") as fh:
            lines = fh.readlines()
            fh.close
        for line in lines:
            userName, password = line.split()
            self.users[userName] = password
            
    def sendFile(self, data, boolEncode):
        if boolEncode:
            while len(data) % 8 != 0:
                data += ' '
            self.client.send(self.des.encrypt(data.encode()))
        else:
            while len(data) % 8 != 0:
                data += b' '
            self.client.send(self.des.encrypt(data))

# Function to be run in a thread to check for keyboard interrupt - Ctrl+C
def checkInterrupt():
    while 1:
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            os._exit(1)

if __name__ == '__main__':
    threading.Thread(target=checkInterrupt).start()
    s = Server()
    s.run()