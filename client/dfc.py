import socket
import sys
import os
import hashlib
from time import sleep
import errno
from Cryptodome.Cipher import DES

class Client():
    def __init__(self):
        self.host = '' 
        self.port = 0
        self.backlog = 5 
        self.size = 1024 
        self.client = None
        self.user = ''
        self.password = ''
        self.filePath = ''
        self.serverAddrs = {}
        self.key = 'datacomm'
        self.des = DES.new(self.key.encode(), DES.MODE_ECB)
    
    #read config file and get the users and passwords and servers
    def checkConf(self):
        if len(sys.argv) == 1:
            print("Please give the path to dfc.conf file as an argument.")
            sys.exit()
        confFile = sys.argv[1]
        if not os.path.exists(confFile):
            print("dfc.conf file not found.")
        with open("./dfc.conf") as fh:
            lines = fh.readlines()
            fh.close()
        for line in lines:
            if (len(line.split()) == 3):
                ser, server, addr = line.split()
                addr = addr.split(':')
                addr[1] = int(addr[1])
                addr = tuple(addr)
                self.serverAddrs[server] = addr
            elif (line.startswith('Username')):
                self.user = line.split(': ')[1].strip()
                self.filePath = "./" + self.user
            elif (line.startswith('Password')):
                self.password = line.split(': ')[1].strip()

    def openSocket(self):
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error or ConnectionError as e:
            print("Error initiating a connection to server.")
            print("Error - ", e)
            sys.exit()
    
    #ask the user to enter a command
    def run(self):
        self.checkConf()
        msg = "menu"
        while 1:
            self.command(msg)
            try:
                print("\nPrint \"Menu\" to print the selection menu again")
                msg = input("Enter your selection: ")
            except (KeyboardInterrupt, EOFError) as e:
                print("Error - ", e)
                sys.exit()

    def command(self, msg):
        method = msg.split()[0].lower()
        fileName = ''
        if (len(msg.split()) > 1):
            if len(msg.split()) == 3:
                fileName = msg.split()[2] + "/" + msg.split()[1]
            else:
                fileName = msg.split()[1] 
        print("file Name- ", fileName)
        if(method == "menu"):
            self.menu()
        elif(method == "get"):
            self.getFile(fileName)
        elif(method == "put"):
            self.putFile(fileName)
        elif(method == "list"):
                self.listFiles(fileName)
#         elif(msg == 4 or msg == "4" or msg == "exit"):
#             exitServer(s, serverAddr)
        else:
            print("Incorrect entry")

    def menu(self):
        print("Please enter a selection from below:\n[1] GET <filename> - Get a file from the server\n[2] PUT <filename> - Send a file to the server\n[3] LIST - List the available files on the server\n")

    #functio to get the file, first get the list of filenames from the servers and then send a request to get the contents of the file
    def getFile(self, fileName):
        self.getFileList = {}
        fileName = self.generateFileNameForGet(fileName)
        if not self.getLfile(fileName):
            print("File not found or cannot be downloaded")
            return
        fileName = self.generateFileNameForSave(fileName)
        directory = '/'.join(fileName.split("/")[:-1])
        self.createDirs(directory)
        with open(fileName, 'wb') as fh:
            for file in sorted(self.getFileList):
                try:
                    if not self.sendCommand("get " + file, self.getFileList[file]):
                        sys.exit()
                    chunkSize = self.des.decrypt(self.client.recv(self.size)).strip().decode()
                    response = self.client.recv(int(chunkSize) + 100)
                    response  = self.des.decrypt(response).strip()
                    fh.write(response)
                except socket.error as err:
                    print("Error - ", err)
                    self.client.close()
                    return
                except Exception as err:
                    print("Error - ", err)
                    self.client.close()
                    return
                self.client.close()
            fh.close()
        print("File Received successfully.")

    def createDirs(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if (exc.errno == errno.EEXIST and os.path.isdir(path)):
                return
    
    def generateFileNameForSave(self, fileName):
        fileName = fileName.replace("\\", "/")
        fileName = fileName.split("/")
        fileName[-1] = fileName[-1][1:]
        fileName = '/'.join(fileName)
        return fileName
    
    def getLfile(self, fileName):
        i = 1
        errCount = 0
        while True:
            if errCount >= 2:
                return False
            serverAddr = self.serverAddrs["DFS" + str(i)]
            try:
                if not self.sendCommand("getl " + fileName, serverAddr):
                    sys.exit()
                response = self.des.decrypt(self.client.recv(self.size)).strip()
                i += 2
                if self.saveGetFileList(response.decode(), serverAddr):
                    return True
                if 'File not found' in self.getFileList.keys():
                    raise Exception
            except socket.error as err:
                if i == 1:
                    i += 2
                i -= 1
                errCount += 1
                print("Error - ", err)
            except Exception as err:
                if i == 1:
                    i += 2
                i -= 1
                errCount += 1
            self.client.close()
        return False

    def saveGetFileList(self, fileList, serverAddr):
        for file in fileList.split("|*|*|"):
            if file == 'File not found':
                self.getFileList[file] = serverAddr
                continue
            file = file.split("/")
            file.pop(0)
            file.pop(0)
            file.pop(0)
            file = '/'.join(file)
            self.getFileList[file] = serverAddr
            
        if len(self.getFileList.keys()) == 4:
            return True
        else:
            return False
                    
    def generateFileNameForGet(self, fileName):
        fileName = fileName.replace("\\", "/")
        fileName = fileName.split("/")
        fileName[-1] = "." + fileName[-1]
        fileName = '/'.join(fileName)
        if fileName.startswith(".") and (not len(fileName.split("/")) == 1):
            fileName = fileName[1:]
            if fileName.startswith("/"):
                fileName = fileName[1:]
        fileName = self.filePath + "/" + fileName
        return fileName
    
    #get the list from all available servers and display to user
    def listFiles(self, fileName):
        fileNames = set()
        for serv in self.serverAddrs.keys():
            try:
                if not self.sendCommand("list " + fileName, self.serverAddrs[serv]):
                    sys.exit()
                response = self.des.decrypt(self.client.recv(self.size)).strip()
                if response.decode() == 'no files found':
                    pass
                files = response.decode().split('|*|*|')
                [fileNames.add(file) for file in files]
            except socket.error as err:
                print("Error - ", err)
            except Exception as err:
                print("Error - ", err)
            self.client.close()
        self.displayFileNamesList(fileNames)
        
    def displayFileNamesList(self, fileNames):
        if len(fileNames) == 0:
            print("No Files found on the server")
            return
        if 'no files found' in fileNames:
            print("Destination Servers unreachable")
            return
        files = {}
        displayList = []
        for file in fileNames:
            file = file.split("/")
            file.pop(0)
            file.pop(0)
            fileTemp = file.pop()[1:-2]
            if (len(file) > 1):
                file = '/'.join(file) + '/' +''.join(fileTemp)
            else:
                file = ''.join(fileTemp)
            
            if file in files.keys():
                files[file] += 1
            else:
                files[file] = 1
        print("\nList of files available for download:")
        for file in files.keys():
            if files[file] == 4:
                displayList.append(file)
                print(file)
            else:
                displayList.append(file + " [incomplete]")
                print(file + " [incomplete]")

    #function to read the file and divide the file contents into chunks and send the contents to the available servers
    def putFile(self, fileName):
        ite = 0
        fileName = fileName.replace("\\", "/")
        if fileName.startswith("."):
            fileName = fileName[1:]
            if fileName.startswith("/"):
                fileName = fileName[1:]
        fileName = self.filePath + "/" + fileName
        if not os.path.exists(fileName):
            print("File does not exist. Please give the correct path to the file.\n\n")
            self.menu()
            return
        fileContents, chunkSize = self.segmentFileContents(fileName)
        div = self.getOrderOfFilesToBeUploaded(fileName)
        fileName = self.generateFileName(fileName)
        it = 0
        for i in range (0, 4):
            serverAddr = self.serverAddrs['DFS' + str((div + it) % 4 + 1)]
            it = it + 1
            try:
                if not self.sendCommand("put " + fileName + "." + str((i % 4) + 1), serverAddr):
                    sys.exit()
                self.sendFile(str(chunkSize + 100), serverAddr, True)
                sleep(2)
                self.sendFile(fileContents[i % 4], serverAddr, False)
                sleep(2)
                self.sendFile(fileContents[(i + 1) % 4], serverAddr, False)
            except socket.error as err:
                print("Error - ", err)
                self.client.close()
                ite += 1
            except Exception as err:
                print("Error - ", err)
                self.client.close()
                ite += 1
            self.client.close()
        if not ((ite == 4) and (ite > 0)):
            print("File uploaded to available servers.")            

    def generateFileName(self, fileName):
        name = fileName.split("/")
        name[-1] = "." + name[-1]
        fileName = '/'.join(name)
        return fileName

    def getOrderOfFilesToBeUploaded(self, fileName):
        hashOfFile = hashlib.md5()
        with open(fileName, 'rb') as fh:
            hashOfFile.update(fh.read())
            fh.close()
        hashOfFile = hashOfFile.hexdigest()
        divideHash = int(hashOfFile, 16) % 4
        return divideHash

    def sendCommand(self, command, serverAddr):
        self.openSocket()
        self.connect(serverAddr)
        command = command + "|*|*|" + self.user + "|*|*|" + self.password
        self.sendFile(command, serverAddr, True)
        if not (command.startswith('getl') or command.startswith('get')):
            self.client.settimeout(1)
        auth = self.des.decrypt(self.client.recv(self.size)).strip()
        if not auth.decode() == 'Authenticated':
            print("Authentication failed with Servers. Please enter the correct Username and Password in dfc.conf")
            return False
        return True

    def connect(self, serverAddr):
        self.client.connect(serverAddr)

    def segmentFileContents(self, fileName):
        buffer = os.path.getsize(fileName)//4 + 1
        fileContents = []
        with open(fileName, 'rb') as fh:
            for i in range(0,4):
                fileContents.append(fh.read(buffer))
            fh.close()
        return fileContents, buffer

    #function to encrypt the data and send to the servers
    def sendFile(self, data, serverAddr, boolEncode):
        if boolEncode:
            while len(data) % 8 != 0:
                data += ' '
            self.client.sendto(self.des.encrypt(data.encode()), serverAddr)
        else:
            while len(data) % 8 != 0:
                data += b' '
            self.client.sendto(self.des.encrypt(data), serverAddr)

if __name__ == "__main__":
    c = Client()
    c.run()