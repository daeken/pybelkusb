import struct, sys

class Packet(object):
	def __init__(self, data):
		(flags, self.seq), data = struct.unpack('>HH', data[:4]), data[4:]
		self.size = 4
		self.flags = flags
		
		if flags == 0x0003:
			unk, unk2, endpoint, unk3, unk4, unk5, size = struct.unpack('>HHBBHLH', data[:14])
			assert unk3 == 0x0001
			assert unk5 == 0x00000000
			print 'Bulk read from endpoint %02X: unk=%04X unk2=%04X unk3=%04X unk4=%04X unk5=%08X size=%04X' % (endpoint, unk, unk2, unk3, unk4, unk5, size)
			print 'Bulk read:  unk=%04X unk2=%04X unk4=%04X' % (unk, unk2, unk4) # Real unknowns
			self.size += 14
		elif flags == 0x8003:
			unk, unk2, endpoint, unk3, unk4, unk5, size = struct.unpack('>HHBBHLH', data[:14])
			assert unk3 == 0x0001
			assert unk5 == 0x00000000
			#print 'Bulk write to endpoint %02X: unk=%04X unk2=%04X unk3=%04X unk4=%04X unk5=%08X size=%04X' % (endpoint, unk, unk2, unk3, unk4, unk5, size)
			#print 'Bulk write: unk=%04X unk2=%04X unk4=%04X' % (unk, unk2, unk4) # Real unknowns
			#print 'Bulk write to endpoint %02X:' % endpoint, 
			#print ' '.join('%02X' % ord(c) for c in data[14:14+size])
			self.size += 14 + size
		elif flags == 0x0001:
			unk, unk2, unk3, unk4, requestType, request, value, index, unk5, size = struct.unpack('>HHHHBBHHHH', data[:18])
			assert unk3 == 0x0201
			assert unk4 == 0x0008
			assert unk5 == 0x0000
			#print 'Control read: reqtype=%02X request=%02X value=%04X index=%04X size=%04X' % (requestType, request, value, index, size)
			self.size += 18
		elif flags == 0x8001:
			unk, unk2, unk3, unk4, requestType, request, value, index, unk5, size = struct.unpack('>HHHHBBHHHH', data[:18])
			assert unk3 == 0x0201
			assert unk4 == 0x0008
			assert unk5 == 0x0000
			#print 'Control write: reqtype=%02X request=%02X value=%04X index=%04X' % (requestType, request, value, index)
			#if size != 0:
			#	print '\tData:', ' '.join('%02X' % ord(c) for c in data[18:18+size])
			
			self.size += 18 + size
		elif flags == 0x0002:
			self.size += 14
		else:
			print '%04X' % flags
			assert True == False
	
	def reply(self, data):
		(flags, seq), data = struct.unpack('>HH', data[:4]), data[4:]
		assert self.seq == seq
		assert self.flags == flags
		size = 4
		
		if flags == 0x0003:
			dsize = struct.unpack('>H', data[4:6])[0]
			size += 6 + dsize
		elif flags == 0x8003:
			size += 6
		elif flags == 0x0001:
			dsize = struct.unpack('>H', data[4:6])[0]
			size += 6 + dsize
		elif flags == 0x8001:
			dsize = struct.unpack('>H', data[4:6])[0]
			size += 6 + dsize
		else:
			assert True == False
		
		return size

class ParseLog(object):
	def __init__(self, log):
		fp = file(log, 'r')
		
		data = ['', '']
		plines = []
		proto, dir, packet = None, None, None
		for line in fp:
			line = line.strip()
			if not len(line):
				continue
			
			if proto == None:
				proto, dir, _ = line.split(' ')
				packet = ''
			elif '|' in line:
				pdata = line.split('|', 1)[1].split('|', 1)[0].replace(' ', '')
				packet += ''.join(chr(int(pdata[i:i+2], 16)) for i in range(0, len(pdata), 2))
				plines.append(line)
			else:
				if proto == 'TCP':
					data[0 if dir == '->' else 1] += packet
				
				proto, dir, packet = None, None, None
				plines = []
		
		packets = {}
		while len(data[0]):
			packet = Packet(data[0])
			packets[packet.seq] = packet
			data[0] = data[0][packet.size:]
		while len(data[1]):
			seq = struct.unpack('>H', data[1][2:4])[0]
			data[1] = data[1][packets[seq].reply(data[1]):]

if __name__=='__main__':
	ParseLog(*sys.argv[1:])
