I've recently been hacking the [Belkin Network USB Hub](http://www.belkin.com/networkusbhub/).  It allows you to connect USB devices to the network and share them between your computers.  The problem?  It's Windows-only and totally undocumented.  The solution?  Reverse-engineering and a Python library, of course.  Btw, if you pick one up, consider getting it from Amazon using my referral link: <iframe src="http://rcm.amazon.com/e/cm?t=iha0a-20&o=1&p=8&l=as1&asins=B000QSN3O6&md=10FE9736YVPPT7A0FBG2&fc1=000000&IS2=1&lt1=_blank&m=amazon&lc1=0000FF&bc1=000000&bg1=FFFFFF&f=ifr" style="width:120px;height:240px;" scrolling="no" marginwidth="0" marginheight="0" frameborder="0"></iframe>

You can find all of the source and some logs in the [pybelkusb](http://github.com/daeken/pybelkusb) repository on Github.  Note that this post is largely stream of consciousness, having been written mostly during the reverse-engineering process, in an effort to show how I actually went about it it, and as such there are certainly inaccuracies and unknowns.  If anyone knows what some of these bits are or manages to find a case that breaks my assumptions, though, drop me a line.

I got it hooked up to my PC via a crossover cable, plugged in some devices (for testing I used an FTDI USB-RS485 cable, a generic flash drive, and a device with a Prolific PL2303 in it), and installed the Belkin software.  Once I'd played around with it a bit -- it works remarkably well, for the record, although the default software is fairly buggy -- I dug in to start hacking it.

I started by breaking out Wireshark and refreshed the device list in the Belkin software, looking to see some basics: protocol (UDP), port number (19540), whether or not encryption/compression is used (unlikely or used sparingly -- plenty of plaintext).  Now, I could've continued using Wireshark, but when I'm reverse-engineering I tend to write my own sniffer using the awesome SharpPcap wrapper for libpcap; this lets me annotate the logs, as well as quickly write parsers so I can validate my assumptions on the fly.  For those of you playing along at home, it's in the Logger directory of the pybelkusb-reverse repo.

So the first thing to figure out was how the Belkin software discovered hubs on the network.  This occurs via a broadcast UDP packet on port 19540:

	0000 | 00 04 95 06 00 00 00 00  00 00 00 00 00 00 00 00  | ..?..... ........ 
	0010 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0020 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0030 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0040 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0050 | 00 00 00 00 00 00 00 00                           | ........ 
	0058

This, as far as I'm aware, is 100% constant.  What the values are, I really can't say however.  The hub responds by sending a UDP packet to the source of the broadcast:

	0000 | 00 02 95 06 00 00 00 00  00 00 00 00 00 00 00 00  | ..?..... ........ 
	0010 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0020 | 00 00 00 00 4e 65 74 77  6f 72 6b 20 55 53 42 20  | ....Netw ork.USB. 
	0030 | 48 75 62 00 00 00 00 00  00 1c df cc 15 dc 00 00  | Hub..... ..??.?.. 
	0040 | 00 00 c0 a8 89 2c 00 00  56 65 72 20 32 2e 32 2e  | ..???,.. Ver.2.2. 
	0050 | 30 00 80 80 00 00 00 00  00 00 00 00 00 00 00 00  | 0.??.... ........ 
	0060 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0070 | 00 00 00 00 42 4b 2d 4e  55 48 43 43 31 35 44 43  | ....BK-N UHCC15DC 
	0080 | 00 00 00 00 31 2e 32 2e  30 00 00 00 00 00 00 00  | ....1.2. 0....... 
	0090 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00a0 | 00 00 00 00 00 00                                 | ......
	00a6

I then worked through the data to figure out the following bits:

- 0x24 [16 bytes] -- Name (null term)
- 0x38 [6 bytes] -- MAC address
- 0x42 [4 bytes] -- IP address
- 0x48 [10 bytes] -- Some version string (null term)
- 0x74 [12 bytes] -- Serial number
- 0x84 [6 bytes] -- Some version string (null term)

Once a hub is discovered, the PC opens a connection (as much as you can with UDP, of course) on port 19540 and sends the following packet to enumerate devices:

	0000 | 00 01 00 01 47 45 54 20  55 53 42 5f 44 45 56 49  | ....GET. USB_DEVI 
	0010 | 43 45 5f 4c 49 53 54 00  00 00 00 00 00 00 00 00  | CE_LIST. ........ 
	0020 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0030 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0040 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0050 | 00 00 00 00 00 00 02 00                           | ........ 
	0058

The structure of that message is pretty clear, but the response less so.  Here are a few responses with varying numbers of devices:

	No devices:
	0000 | 00 01 00 00 00 00 00 01  00 00 00 00 00 00 00 00  | ........ ........ 
	0010 | 00 00                                             | ..
	0012

	1 device:
	0000 | 00 01 00 00 00 00 00 39  01 64 65 76 30 31 00 55  | .......9 .dev01.U 
	0010 | 53 42 32 2e 30 20 46 6c  61 73 68 20 44 69 73 6b  | SB2.0.Fl ash.Disk 
	0020 | 00 00 00 00 00 80 81 12  21 32 34 48 31 34 00 00  | .....??. !24H14.. 
	0030 | 00 00 00 00 00 00 00 00  00 00 00 00 08 00 00 00  | ........ ........ 
	0040 | 00                                                | .
	0041

	2 devices:
	0000 | 00 01 00 00 00 00 00 74  02 64 65 76 30 31 00 55  | .......t .dev01.U
	0010 | 53 42 32 2e 30 20 46 6c  61 73 68 20 44 69 73 6b  | SB2.0.Fl ash.Disk
	0020 | 00 00 00 00 00 80 81 12  21 32 34 48 31 34 00 00  | .....??. !24H14..
	0030 | 00 00 00 00 00 00 00 00  00 00 00 00 08 00 00 00  | ........ ........
	0040 | 00 64 65 76 30 32 00 46  54 44 49 20 55 53 42 2d  | .dev02.F TDI.USB-
	0050 | 52 53 34 38 35 20 43 61  62 6c 65 00 00 00 00 00  | RS485.Ca ble.....
	0060 | 80 81 04 03 60 01 46 32  33 00 00 00 00 00 00 00  | ??..`.F2 3.......
	0070 | 00 00 00 00 00 00 00 ff  00 00 00 00              | .......? ....
	007c

At first I was a bit thrown off by the varying packet size, until I realized that it actually just uses null-terminated strings.  The structure from there is pretty straightforward, although certain bits are still unknown/assumed constant:

- 0x00 -- Header (`00 01 00 00 00 00 00`)
- 0x07 [1 byte] -- Packet size - 8
- 0x08 [1 byte] -- Number of devices
- For each device
	- Device node, null terminated string (devXX)
	- Device name, null terminated string
	- 4 byte IP of computer connected to device, or nulls if it's open
	- `80 81`
	- 2 bytes Vendor ID
	- 2 bytes Product ID
	- 22 bytes of unknown data

After a short break to implement hub discovery and device enumeration (quite simple with Python), I started capturing data for device connection.  The following is a request to connect to the flash drive, on device node `dev01`.

	0000 | 00 01 00 01 45 58 45 43  20 53 43 41 4e 4e 45 52  | ....EXEC .SCANNER 
	0010 | 20 43 4f 4e 4e 45 43 54  3a 01 06 00 1c df cc 15  | .CONNECT :....??. 
	0020 | dc c0 a8 89 01 64 65 76  30 31 00 4c 54 00 00 00  | ????.dev 01.LT... 
	0030 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0040 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0050 | 00 00 00 00 00 00 02 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0060 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0070 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0080 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0090 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00a0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00b0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00c0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00d0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00e0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00f0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0100 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0110 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0120 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0130 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0140 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0150 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0160 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0170 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0180 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0190 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01a0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01b0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01c0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01d0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01e0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01f0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00        | ........ ......
	01fe

Holy nulls, batman!  As you can see, most of this packet is unused, and it's almost entirely constant:

- 0x00 [4 bytes] -- `00 01 00 01`
- 0x04 [21 bytes] -- `EXEC SCANNER CONNECT:`
- 0x19 [3 bytes] -- `01 06` (06 could be the length of the following field, a MAC address)
- 0x1A [6 bytes] -- MAC address of the hub
- 0x21 [4 bytes] -- IP address of the computer
- 0x25 [6 bytes] -- Device node string, null terminated
- 0x2B [3 bytes] -- `LT` followed by a null
- 0x2E [40 bytes] -- Nulls
- 0x56 [1 byte] -- `02`
- 0x57 [423 bytes] -- Nulls

The hub responds as follows for success:

	0000 | 00 01 00 00 00 00 00 03  4f 4b 00 76 30 31 00 55  | ........ OK.v01.U 
	0010 | 53 42                                             | SB
	0012

Or for failure:

	0000 | 00 01 00 00 00 00 00 03  4e 47 00 76 30 31 00 55  | ........ NG.v01.U 
	0010 | 53 42                                             | SB
	0012

This one should be pretty self-explanatory, but regardless:

- 0x00 [4 bytes] -- `00 01 00 00`
- 0x04 [4 bytes] -- `00 00 00 03` Potentially the size of the following string
- 0x08 [3 bytes] -- `OK`/`NG` followed by a null
- 0x0B [4 bytes] -- `v01` followed by a null
- 0x0F [3 bytes] -- `USB`

Now it gets a bit tricky.  You send the connection packet a second time, and the hub sends two UDP packets to port 19540 on the PC.  Note: this is _not_ where you sent the broadcasts from, it is a port you have to have hold open explicitly for device connections/disconnections.  Also, a few things to be aware of if you're talking to the hub from Windows: The SXUPTP driver that handles the hub communication holds this port at all times, and if you connect to a device from, e.g. pybelkusb, and don't have the Belkin GUI up, the driver will crash and cause a kernel panic.  This bit me in the ass repeatedly.  Anyway, here's the packets it sends:

	0000 | 29 08 02 05 c0 a8 89 2c  30 32 30 31 00 00 00 00  | )...???, 0201.... 
	0010 | 01 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0020 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0030 | 46 32 33 00 00 00 00 00  00 00 00 00 00 00 00 00  | F23..... ........ 
	0040 | 12 01 02 00 00 00 00 08  04 03 60 01 06 00 01 02  | ........ ..`..... 
	0050 | 03 01 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0060 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0070 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0080 | 09 02 00 20 01 01 00 80  96 09 04 00 00 02 ff ff  | .......? ?.....?? 
	0090 | ff 02 07 05 81 02 00 40  00 07 05 02 02 00 40 00  | ?...?..@ ......@. 
	00a0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00b0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00c0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00d0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00e0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	00f0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0100 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0110 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0120 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0130 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0140 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0150 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0160 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0170 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0180 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0190 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01a0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01b0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01c0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01d0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01e0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	01f0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0200 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0210 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0220 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0230 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0240 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0250 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0260 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0270 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0280 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0290 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	02a0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	02b0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	02c0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	02d0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	02e0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	02f0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0300 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0310 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0320 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0330 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0340 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0350 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0360 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0370 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0380 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0390 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	03a0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	03b0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	03c0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	03d0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	03e0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	03f0 | 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  | ........ ........ 
	0400

	0000 | 00 03 00 00 00 00 00 00  30 32 30 31 00 00 00 00  | ........ 0201.... 
	0010 | 01 00                                             | ..
	0012

I never really figured out the meaning of either of these packets.  The one thing I do know is that the fourth byte of the first packet there is some sort of device ID for the duration of the connection.  You'll see it in use shortly.

Once these packets are receieved, you can make an actual connection to the device.  You do this by connecting to TCP port 19540 on the hub.  No initialization is required on the connection, and you can start sending commands.  Let's see a bulk write:

	TCP -> hub
	0000 | 80 03 03 10 00 02 05 02  02 01 80 40 00 00 00 00  | ?....... ..?@.... 
	0010 | 00 10 66 6f 6f 20 62 61  72 20 62 61 7a 20 68 61  | ..foo.ba r.baz.ha 
	0020 | 78 21                                             | x!
	0022

The data `foo bar baz hax!` was sent to endpoint 0x02 in this case, and the structure is as follows:

- 0x04 [2 bytes] -- Endpoint number (think this is two bytes, might be 1 at 0x05)
- 0x10 [2 bytes] -- Size of data
- 0x12 -- Data to write

Now, here I'll break from the narrative to explain the rest of the structure and a bit about the TCP "packets" themselves.  Each TCP packet begins with two bytes indicating its type, e.g. `80 03` == bulk write.  This is followed by a two-byte sequence, which starts at zero.  Figuring out the rest of it took writing a parser that was capable of churning through a dozen logs I took over a period of a week.  There are still unknown bits, but here's the best I managed to do:

- 0x04 [2 bytes] -- Unknown (I always send `00 03`)
- 0x06 [1 byte] -- Device ID referred to above
- 0x07 [1 byte] -- Constant `02`
- 0x08 [1 byte] -- Endpoint number
- 0x09 [1 byte] -- Constant `01`
- 0x0A [2 bytes] -- Unknown (I always send `80 40`)
- 0x0C [4 bytes] -- Constant `00 00 00 00`
- 0x10 [2 bytes] -- Size of data
- 0x12 -- Data

The hub responds:

	TCP <- hub
	0000 | 80 03 03 10 00 00 00 00  00 00                    | ?....... ..
	000a

Note that the type (`80 03`) and sequence number (`03 01`) match up with the packet sent to the device.  The rest of the packet is null in every case I've seen.  This may be used for errors in some case, but I've yet to actually see that.

I implemented this, then realized I needed control writes to actually initialize the device I intended to speak to, so that was up next.  Here's an example control write:

	TCP -> hub
	0000 | 80 01 03 11 00 02 05 00  02 01 00 08 40 01 01 00  | ?....... ....@... 
	0010 | 00 00 00 00 00 00                                 | ......
	0016

Here you can see the type is `80 01`.  The packet structure is:

- 0x04 [2 bytes] -- Unknown (I always send `00 03`)
- 0x06 [1 byte] -- Device ID referred to above
- 0x07 [1 byte] -- Null
- 0x08 [4 bytes] -- Constant `02 01 00 08`
- 0x0C [1 byte] -- Request type
- 0x0D [1 byte] -- Request
- 0x0E [2 bytes] -- Value
- 0x10 [2 bytes] -- Index
- 0x12 [2 bytes] -- Null
- 0x14 [2 bytes] -- Size of data
- 0x16 -- Data

This one was particularly difficult to track down, as a lot of the values look the same and I had no idea which was which.  It took installing a USB sniffer on my computer and capturing the actual device initialization and going over it field-by-field, matching the locations.  I won't bore you with the details of that -- if you're interested, grab the demo of USBTrace and give it a shot; it's not hard.

The hub responds:


	TCP <- hub
	0000 | 80 01 03 11 00 00 00 00  00 00                    | ?....... ..
	000a

Much like bulk writes, it's an empty packet with matching type/sequence.

With bulk writes and control writes out of the way, the matching two were dead simple, as almost everything is identical.  A control read:

	TCP -> hub
	0000 | 00 01 00 05 00 02 05 00  02 01 00 08 80 06 03 02  | ........ ....?... 
	0010 | 04 09 00 00 00 ff                                 | .....?
	0016

The structure is identical to the control write message, with the exception of byte 0x5.  In this case, I send 1 constantly, but I don't really think it matters.  Of course, there's no data following this packet, since the size indicates the number of bytes to read.

Response:

	TCP <- hub
	0000 | 00 01 00 05 00 00 00 00  00 20 20 03 55 00 53 00  | ........ ....U.S. 
	0010 | 42 00 2d 00 52 00 53 00  34 00 38 00 35 00 20 00  | B.-.R.S. 4.8.5... 
	0020 | 43 00 61 00 62 00 6c 00  65 00                    | C.a.b.l. e.
	002a

The structure here is dead simple, and you most likely could figure it out in under a minute, having made it this far:

- 0x04 [4 bytes] -- Nulls
- 0x08 [2 bytes] -- Size read
- 0x0A -- Data

Bulk reads are likewise simple as hell:

	TCP -> hub
	0000 | 00 03 03 6e 00 01 04 81  02 01 82 00 00 00 00 00  | ...n...? ..?..... 
	0010 | 02 00                                             | ..
	0012

Raise your hand if you're surprised that this is identical to the bulk write.  None of you?  Thought so.  I won't insult your intelligence by breaking this down.

The response:

	TCP <- hub
	0000 | 00 03 03 6e 00 00 00 00  02 00 eb 3c 90 4d 53 57  | ...n.... ..?<?MSW 
	0010 | 49 4e 34 2e 31 00 02 40  06 00 02 00 7e 00 00 f8  | IN4.1..@ ....~..? 
	0020 | fd 00 3f 00 ff 00 00 00  00 00 00 20 3f 00 00 00  | ?.?.?... ....?... 
	0030 | 29 22 96 1b 00 4e 4f 20  4e 41 4d 45 20 20 20 20  | )"?..NO. NAME.... 
	0040 | 46 41 54 31 36 20 20 20  fa 33 c0 8e d0 bc 00 7c  | FAT16... ?3????.| 
	0050 | 16 07 bb 78 00 36 c5 37  1e 56 16 53 bf 3e 7c b9  | ..?x.6?7 .V.S?>|? 
	0060 | 0b 00 fc f3 a4 06 1f c6  45 fe 0f 8b 0e 18 7c 88  | ..???..? E?.?..|? 
	0070 | 4d f9 89 47 02 c7 07 3e  7c fb cd 13 72 79 33 c0  | M??G.?.> |??.ry3? 
	0080 | 39 06 13 7c 74 08 8b 0e  13 7c 89 0e 20 7c a0 10  | 9..|t.?. .|?..|?. 
	0090 | 7c f7 26 16 7c 03 06 1c  7c 13 16 1e 7c 03 06 0e  | |?&.|... |...|... 
	00a0 | 7c 83 d2 00 a3 50 7c 89  16 52 7c a3 49 7c 89 16  | |??.?P|? .R|?I|?. 
	00b0 | 4b 7c b8 20 00 f7 26 11  7c 8b 1e 0b 7c 03 c3 48  | K|?..?&. |?..|.?H 
	00c0 | f7 f3 01 06 49 7c 83 16  4b 7c 00 bb 00 05 8b 16  | ??..I|?. K|.?..?. 
	00d0 | 52 7c a1 50 7c e8 92 00  72 1d b0 01 e8 ac 00 72  | R|?P|??. r.?.??.r 
	00e0 | 16 8b fb b9 0b 00 be e6  7d f3 a6 75 0a 8d 7f 20  | .???..?? }??u.?.. 
	00f0 | b9 0b 00 f3 a6 74 18 be  9e 7d e8 5f 00 33 c0 cd  | ?..??t.? ?}?_.3?? 
	0100 | 16 5e 1f 8f 04 8f 44 02  cd 19 58 58 58 eb e8 8b  | .^.?.?D. ?.XXX??? 
	0110 | 47 1a 48 48 8a 1e 0d 7c  32 ff f7 e3 03 06 49 7c  | G.HH?..| 2???..I| 
	0120 | 13 16 4b 7c bb 00 07 b9  03 00 50 52 51 e8 3a 00  | ..K|?..? ..PRQ?:. 
	0130 | 72 d8 b0 01 e8 54 00 59  5a 58 72 bb 05 01 00 83  | r??.?T.Y ZXr?...? 
	0140 | d2 00 03 1e 0b 7c e2 e2  8a 2e 15 7c 8a 16 24 7c  | ?....|?? ?..|?.$| 
	0150 | 8b 1e 49 7c a1 4b 7c ea  00 00 70 00 ac 0a c0 74  | ?.I|?K|? ..p.?.?t 
	0160 | 29 b4 0e bb 07 00 cd 10  eb f2 3b 16 18 7c 73 19  | )?.?..?. ??;..|s. 
	0170 | f7 36 18 7c fe c2 88 16  4f 7c 33 d2 f7 36 1a 7c  | ?6.|???. O|3??6.| 
	0180 | 88 16 25 7c a3 4d 7c f8  c3 f9 c3 b4 02 8b 16 4d  | ?.%|?M|? ????.?.M 
	0190 | 7c b1 06 d2 e6 0a 36 4f  7c 8b ca 86 e9 8a 16 24  | |?.??.6O |?????.$ 
	01a0 | 7c 8a 36 25 7c cd 13 c3  0d 0a 4e 6f 6e 2d 53 79  | |?6%|?.? ..Non-Sy 
	01b0 | 73 74 65 6d 20 64 69 73  6b 20 6f 72 20 64 69 73  | stem.dis k.or.dis 
	01c0 | 6b 20 65 72 72 6f 72 0d  0a 52 65 70 6c 61 63 65  | k.error. .Replace 
	01d0 | 20 61 6e 64 20 70 72 65  73 73 20 61 6e 79 20 6b  | .and.pre ss.any.k 
	01e0 | 65 79 20 77 68 65 6e 20  72 65 61 64 79 0d 0a 00  | ey.when. ready... 
	01f0 | 49 4f 20 20 20 20 20 20  53 59 53 4d 53 44 4f 53  | IO...... SYSMSDOS 
	0200 | 20 20 20 53 59 53 00 00  55 aa                    | ...SYS.. U?
	020a

Again, the structure screams out at this point.

And really, that's about it.  I didn't cover disconnection because it's boring and dead simple (see the source in pybelkusb if you're really curious, or just log the disconnection yourself and look at it), and I haven't yet looked into error handling or timeouts whatsoever (they'll make their way into pybelkusb soon enough), but I think this gives you a good idea of how the protocol works and how easy it really is to reverse-engineer protocols like this.

Happy Hacking,  
- Cody Brocious (Daeken)