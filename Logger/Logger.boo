import PacketDotNet
import SharpPcap
import System
import System.Net
import System.Text
import System.Threading

class Logger:
	printable = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789~!@#$%^&*()_+`-=[]{}\\|;:\'",./<>?'
	HubIp = IPAddress.Parse('192.168.137.44')
	
	def constructor(device as LivePcapDevice):
		device.OnPacketArrival += do(o, packet):
			ppacket = Packet.ParsePacket(packet.Packet)
			upacket = UdpPacket.GetEncapsulated(ppacket)
			if upacket != null and (upacket.SourcePort == 19540 or upacket.DestinationPort == 19540):
				HandlePacket('UDP', upacket.SourcePort == 19540, upacket.PayloadData)
			else:
				tpacket = TcpPacket.GetEncapsulated(ppacket)
				if tpacket != null and (tpacket.SourcePort == 19540 or tpacket.DestinationPort == 19540) and len(tpacket.PayloadData) > 0:
					HandlePacket('TCP', tpacket.SourcePort == 19540, tpacket.PayloadData)
		
		device.Open()
		device.StartCapture()
		
		try:
			while true:
				Thread.Sleep(1)
		except:
			pass
		
		device.StopCapture()
		device.Close()
	
	def HandlePacket(proto as string, fromHub as bool, data as (byte)):
		Dump(
				proto,
				fromHub, 
				data
			)
	
	def Dump(protocol, fromHub as bool, data as (byte)):
		if fromHub:
			print '{0} <- hub' % (protocol, )
		else:
			print '{0} -> hub' % (protocol, )
		
		for i in range(0, len(data), 16):
			line = '{0:x4} | ' % (i, )
			for j in range(i, i+16):
				if j >= len(data):
					line += '   '
				else:
					line += '{0:x2} ' % (data[j], )
				if j % 8 == 7:
					line += ' '
			line += '| '
			for j in range(i, Math.Min(i+16, len(data))):
				try:
					c = ASCIIEncoding.ASCII.GetString((data[j], ))
				except:
					c = '.'
				if c in printable:
					line += c
				else:
					line += '.'
				if j % 8 == 7:
					line += ' '
			print line
		print '{0:x4}' % (len(data), )
		print

if len(argv) > 0:
	addr = argv[0]
else:
	addr = null
found = false
for device in LivePcapDeviceList.Instance:
	for address in device.Interface.Addresses:
		if address.Addr.type == Sockaddr.Type.AF_INET_AF_INET6:
			if addr == null or address.Addr.ToString() == addr:
				Logger(device)
				found = true
				break
	if found:
		break
