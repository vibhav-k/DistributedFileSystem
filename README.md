# DistributedFileSystem

## [Version]
Python version - 3.4.4 

## [Files]
Files included:
	- dfc.py
	- dfc.conf
	- dfs.py
	- dfs.conf
## [Usage]
How to run the DFC script
1. To run the dfc.py scripts, run below command:
	dfc.py [path/to/dfc.conf]

How to run the DFS scripts
1. To run the dfs.py script, run below command
	dfs.py [DFS_directory] [port_number]

## [About]
dfc.py & dfs.py
1. On running dfc.py script, user will be provided with a list of option
	GET filename
	PUT filename
	LIST
2. On entering the command, the client will connect to each of the 4 DFS servers and send a command along with the username and password stored in the dfc.conf file.
3. Whatever data sent and received by the client is encrypted before sending and decrypted on receiving.
4. Client will decide how to split the file into 4 chunks and where to send each of the chunks.
5. For receiving, the client will check on either server 1 and 3 or server 2 and 4 for the file and send the request for getting the file contents.
6. The dfs also supported sub directories.
7. For traffic optimization, the client will first check on server 1. If the files are available on server 1, it will then contact server 3. If server 1 is not available then it will connect to server 2. If server 2 is also unavailable then it will inform the user that the file cannot be downloaded. If server 2 is available, then the client script connects to server 4 and gets the file names. 
8. Then the client script will send a command to get the file contents from the available servers.
