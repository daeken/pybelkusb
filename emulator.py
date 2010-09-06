from socket import *

printable = 'abcdefghijklmnopqrstuvwxyz'
printable += printable.upper()
printable += ''.join(map(str, range(10)))
printable += '~!@#$%^&*()_+`-=[]{}\\|;:\'",./<>?'

class PacketParser(object):
	def __init__(self, data):
		self.data = data
		self.off = 0
		
		if hasattr(self, 'parse'):
			self.parse()
	
	def read(self, type, size=None):
		if isinstance(type, int):
			type, size = str, type
		if type == str:
			if size == None:
				ret = ''
				while self.data[self.off] != '\0':
					ret += self.data[self.off]
					self.off += 1
				self.off += 1
			else:
				ret = self.data[self.off:self.off + size]
				self.off += size
		return ret
	
	def dump(self):
		for i in range(0, len(self.data), 16):
			print '%04X |' % i, 
			for j in range(i, i+16):
				if j < len(self.data):
					print '%02X' % ord(self.data[j]), 
				else:
					print '  ', 
				if j & 0xF == 0x7:
					print '', 
			print '|', 
			chars = ''
			for j in range(i, min(len(self.data), i + 16)):
				c = self.data[j]
				if c in printable:
					chars += c
				else:
					chars += '.'
				if j & 0xF == 0x7:
					chars += ' '
			print chars
		
		print '%04X' % len(self.data)

class Emulator(object):
	def __init__(self):
		self.sock = socket(AF_INET, SOCK_DGRAM, SOL_UDP)
		self.sock.bind(('', 19540))
		self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		
		discoverPacket = '\x00\x04\x95\x06' + '\0'*84
		discoverRespPacket = '\x00\x02\x95\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Network USB Hub\x00\x00\x00\x00\x00\x00\x17\x3f\x50\xaf\x65\x00\x00\x00\x00\xc0\xa8\x01\x12\x00\x00Ver 2.2.0\x00\x80\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00BK-NUHCC15DC\x00\x00\x00\x001.2.0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
		deviceListPacket = 'GET USB_DEVICE_LIST'
		while True:
			packet, addr = self.sock.recvfrom(65536)
			if packet == discoverPacket:
				self.sock.sendto(discoverRespPacket, 0, addr)
			elif packet[4:].startswith(deviceListPacket):
				packet = '\x00\x01\x00\x00\x00\x00\x00'
				rest = chr(1)
				rest += 'dev01\0Foo device!\0'
				rest += '\x00\x00\x00\x00\x80\x81\x04\x03`\x01F22\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00\x00'
				packet += chr(len(rest)) + rest
				self.sock.sendto(packet, 0, addr)
			else:
				PacketParser(packet).dump()

Emulator()
