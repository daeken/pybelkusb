from select import *
from socket import *
import struct

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
		elif type == int:
			if size == 1:
				ret = ord(self.data[self.off])
				self.off += 1
			elif size == 2:
				ret = (ord(self.data[self.off]) << 8) | ord(self.data[self.off+1])
				self.off += 2
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

class Device(object):
	def __init__(self, hub, node, name, vid, pid):
		self.hub, self.sock = hub, hub.sock
		self.node, self.name, self.vid, self.pid = node, name, vid, pid
		print '%s -- %r (%04X:%04X)' % (node, name, vid, pid)
		
		self.tsock = None
	
	def connect(self):
		self.connected = True
		
		packet = '\x00\x01\x00\x01'
		packet += 'EXEC SCANNER CONNECT:'
		packet += '\x01\x06'
		packet += self.hub.mac
		packet += '\xc0\xa8\x89\x01'
		packet += self.node + '\0LT\0' + '\0'*40 + '\x02' + '\0'*423
		self.sock.send(packet)
		PacketParser(self.sock.recv(65536)).dump()
		
		packet = '\x00\x03\x00\x01'
		packet += 'EXEC SCANNER CONNECT:'
		packet += '\x01\x06'
		packet += self.hub.mac
		packet += '\xc0\xa8\x89\x01'
		packet += self.node + '\0LT\0' + '\0'*39 + '\x03\x02' + '\0'
		self.sock.send(packet)
		self.sock.recv(65536)
		self.devId = ord(Hub.bcsock.recv(65536)[3]) # total hack!
		
		self.tsock = socket(AF_INET, SOCK_STREAM)
		self.tsock.bind(('', 0))
		self.tsock.connect(self.hub.addr)
		
		self.seq = 0
		self.controlRead(requestType=0x80, request=0x06, value=0x0100, size=0x12)
	
	def controlRead(self, requestType, request, value=0, index=0, size=0):
		packet = '\x00\x01' + chr(self.seq >> 8) + chr(self.seq & 0xFF)
		self.seq += 1
		packet += struct.pack(
				'>HHHHBBHHHH', 
				0x0001, 
				self.devId << 8,
				0x0201, # constant
				0x0008, # constant
				requestType, 
				request, 
				value, 
				index, 
				0x0000, # constant
				size
			)
		self.tsock.send(packet)
		#PacketParser(packet).dump()
		resp = self.tsock.recv(65536)
		#PacketParser(resp).dump()
	
	def controlWrite(self, requestType, request, value=0, index=0, buf=None):
		packet = '\x80\x01' + chr(self.seq >> 8) + chr(self.seq & 0xFF)
		self.seq += 1
		packet += struct.pack(
				'>HHHHBBHHHH', 
				0x0003, 
				self.devId << 8,
				0x0201, # constant
				0x0008, # constant
				requestType, 
				request, 
				value, 
				index, 
				0x0000, # constant
				0 if buf == None else len(buf)
			)
		if buf != None:
			packet += buf
		self.tsock.send(packet)
		resp = self.tsock.recv(65536)
		#PacketParser(resp).dump()
	
	def bulkWrite(self, endpoint, data):
		packet = '\x80\x03' + chr(self.seq >> 8) + chr(self.seq & 0xFF)
		self.seq += 1
		packet += struct.pack(
				'>HHBBHLH', 
				0x0003, 
				(self.devId << 8) | 0x02,
				endpoint, 
				0x01, 
				0x8040, 
				0x00000000, 
				len(data)
			)
		packet += data
		self.tsock.send(packet)
		
		resp = self.tsock.recv(65536)
		#PacketParser(resp).dump()
	
	def bulkRead(self, endpoint, size):
		data = ''
		while size > 0:
			packet = '\x00\x03' + chr(self.seq >> 8) + chr(self.seq & 0xFF)
			self.seq += 1
			packet += struct.pack(
					'>HHBBHLH', 
					0x0003, 
					(self.devId << 8) | 0x83,
					endpoint, 
					0x01, 
					0x8040, 
					0x00000000, 
					size
				)
			self.tsock.send(packet)
			
			resp = self.tsock.recv(65536)
			data += resp[10:]
			size -= len(resp) - 10
		return data
	
	def disconnect(self):
		#assert self.connected and self.tsock != None
		self.connected = False
		
		packet = '\x00\x01\x00\x64'
		packet += 'EXEC SCANNER DISCONNECT:'
		packet += '\x01\x06'
		packet += self.hub.mac
		packet += '\xc0\xa8\x89\x01'
		packet += self.node + '\0'
		packet += '\0' * 42
		packet += '\x02'
		packet += '\0' * 423
		self.sock.send(packet)
		
		PacketParser(self.sock.recv(65536)).dump()

class DeviceListPacket(PacketParser):
	def parse(self):
		self.dump()
		assert self.data[:7] == '\x00\x01\x00\x00\x00\x00\x00'
		assert len(self.data) == ord(self.data[7]) + 8
		
		devCount = ord(self.data[8])
		self.off = 9
		self.devs = []
		for i in range(devCount):
			node, name = self.read(str), self.read(str)
			
			ip = self.read(str, 4)
			flags = self.read(str, 2)
			vid = self.read(int, 2)
			pid = self.read(int, 2)
			unk = self.read(str, 22)
			
			self.devs.append((node, name, vid, pid))

class Hub(object):
	def __init__(self, packet, addr, mac):
		self.addr = addr
		self.mac = mac
		self.sock = socket(AF_INET, SOCK_DGRAM, SOL_UDP)
		self.sock.bind(('', 0))
		self.sock.connect(addr)
	
	@property
	def devices(self):
		self.sock.send('\x00\x01\x00\x01GET USB_DEVICE_LIST' + '\0'*0x4F + '\x02\x00')
		packet = DeviceListPacket(self.sock.recv(65536))
		
		return [Device(self, *device) for device in packet.devs]
	
	@staticmethod
	def discover():
		if hasattr(Hub, 'bcsock'):
			sock = Hub.bcsock
		else:
			Hub.bcsock = sock = socket(AF_INET, SOCK_DGRAM, SOL_UDP)
			sock.bind(('192.168.137.1', 19540))
			sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
			sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		sock.sendto('\x00\x04\x95\x06' + '\0'*84, 0, ('255.255.255.255', 19540))
		
		hubs = []
		while True:
			r, _, __ = select((sock, ), (), (), 1)
			if len(r):
				packet, addr = sock.recvfrom(65536)
				if packet[:4] == '\x00\x02\x95\x06':
					hubs.append(Hub(packet, addr, packet[0x38:0x38+6]))
			else:
				break
		return hubs
	
	@staticmethod
	def enumerate(vid=None, pid=None, name=None):
		devices = []
		for hub in Hub.discover():
			for device in hub.devices:
				if vid != None and device.vid != vid:
					continue
				elif pid != None and device.pid != pid:
					continue
				elif name != None and device.name != name:
					continue
				devices.append(device)
		return devices
