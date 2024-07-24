
import serial
import time
import re
import serial.tools.list_ports


def find_port():
	comlist = list(serial.tools.list_ports.comports())
	count=1;
	for element in comlist:
		print(count,"->",element)
		count+=1
	n=int(input("enter which port you want to connect to"))
	string=""
	port=str(comlist[n-1])
	print(port)
	string=port.split(' ')[0]
	#print(string)
	return string
port=find_port() 
ser=serial.Serial(port,115200)
"""f=open('log_2.txt','w')	
while True:
	try:
		x=ser.readline()
		y=str(x,'UTF-8')
		print(y)
		f.write(y)
	except Exception as e:
		ser.close()"""