import struct
import spyder
import os
def getAuthenticode64(x):
    PE_start = struct.unpack("<I",data[0x3c:0x40])[0]
    offset,size = struct.unpack("<II",data[PE_start+0x18+144:PE_start+0x18+144+8])
    return x[offset:offset+size]

spyder.loadStructuresDefs(file(r"rfcs\X.509Structures.txt","rb").read())
spyder.loadStructuresDefs(file(r"rfcs\pkcs7Structures.txt","rb").read())
spyder.loadStructuresDefs(file(r"rfcs\moreStructures.txt","rb").read())

ac = spyder.buildTemplate("SignedData")
print "Reading ntoskrnl.exe as an example file..."
if os.path.exists(r"c:\windows\sysnative\ntoskrnl.exe"):
    data = file(r"c:\windows\sysnative\ntoskrnl.exe","rb").read()
elif os.path.exists(r"c:\windows\system32\ntoskrnl.exe"):
    data = file(r"c:\windows\system32\ntoskrnl.exe","rb").read()
else:
    print "Couldn't find 64bit ntoskrnl.exe!"
    assert False
x = getAuthenticode64(data)[8:]
t = spyder.Any()
t.loadFromBytes(x)
z = t[1][0].getEncoded()
ac.loadFromBytes(z)
spyder.setMaxPrintRecursion(3)
print ac
