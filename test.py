from hub import Hub
import struct

class PL2303(object):
	def __init__(self):
		self.device = None
		for device in Hub.enumerate(vid=0x067B, pid=0x2303):
			device.connect()
			self.device = device
			break
		assert self.device != None
		
		self.device.controlWrite(requestType=0x40, request=0x01, value=0x0002, index=0x0044) #w(0x0002, 0x0044)
		
		baud = 9600
		setupBuf = struct.pack('<L', baud)
		setupBuf += '\0' # 1 stop bit
		setupBuf += '\0' # No parity
		setupBuf += '\x08' # Unk
		self.device.controlWrite(request=0x20, requestType=0x21, buf=setupBuf)
	
	def write(self, data):
		self.device.bulkWrite(endpoint=0x02, data=data)
	
	def read(self, size):
		return self.device.bulkRead(endpoint=0x02, size=size)
	
	def close(self):
		self.device.disconnect()

import time

device = PL2303()
device.write('\x1Bz' + chr(40) + chr(40))
assert device.read(2) == '\x1B0'

for i in range(10):
	device.write('\x1B\x81')
	time.sleep(0.25)
	device.write('\x1B\x82')
	time.sleep(0.25)
device.close()
