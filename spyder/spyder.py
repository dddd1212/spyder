UNIVERSAL_CLASS = 0
APPLICATION_CLASS = 1
CONTEXT_SPECIFIC_CLASS = 2
PRIVATE_CLASS = 3

BOOLEAN_TAG_NUMBER = 1
INTEGER_TAG_NUMBER = 2
BIT_STRING_TAG_NUMBER = 3
OCTET_STRING_TAG_NUMBER = 4
NULL_TAG_NUMBER = 5
OID_TAG_NUMBER = 6

UTF8STRING_TAG_NUMBER = 12
NUMERICSTRING_TAG_NUMBER = 18
PRINTABLESTRING_TAG_NUMBER = 19
TELETEXSTRING_TAG_NUMBER = 20
VIDEOTEXSTRING_TAG_NUMBER = 21
IA5STRING_TAG_NUMBER = 22
UTCTIME_TAG_NUMBER = 23
GENERALIZED_TIME_TAG_NUMBER = 24
GRAPHICSTRING_TAG_NUMBER = 25
VISIBLESTRING_TAG_NUMBER = 26
GENERALSTRING_TAG_NUMBER = 27
UNIVERSALSTRING_TAG_NUMBER = 28
BMPSTRING_TAG_NUMBER = 30

SEQUENCE_TAG_NUMBER = 16
SET_TAG_NUMBER = 17
class DERTypeError(Exception):
    pass
    #def __init__(self,e):
    #    print "DERTypeError[%s]"%e
    #    super(DERTypeError,self).__init__(e)

_console_width = 80
def _get_console_width():
    global _console_width
    return _console_width

def _set_console_width(width):
    global _console_width
    _console_width = width

_maxPrintRecursion = -1
def setMaxPrintRecursion(num):
    global _maxPrintRecursion
    _maxPrintRecursion = num
    
class DERBase:
    def __init__(self, Tag:int, Class:int, Constructed:bool):
        self._wrappable = []
        self.Tag = Tag
        self.Class = Class
        self._Constructed = Constructed

    def __repr__(self):
        return self._getIndentedPrintable(0,"")

    def getContentOctets(self) -> bytes:
        raise Exception("Cannot get content octets of abstract DERBase")
    
    def getEncoded(self) -> bytes:
        encContent = self.getContentOctets()
        if self.Tag <= 30:
            encType = bytes([(self.Class<<6) + self._Constructed*(1<<5) + (self.Tag)])
        else:
            c = self.Tag
            r = bytes([c&0x7f])
            c>>=7
            while c > 0:
                r += bytes([(c&0x7f)+0x80])
                c>>=7
                
            encType = bytes([(self.Class<<6)+self._Constructed*(1<<5)+0b11111])+r[::-1]
            
        contentLength = len(encContent)
        if contentLength < 0x80:
            encLength = bytes([contentLength])
        else:
            r = b""
            c = contentLength
            while c >= 0x100:
                r += bytes([c&0xff])
                c>>=8
            r+=bytes([c])
            encLength = bytes([0x80+len(r)])+r[::-1]
        return encType+encLength+encContent
    
    # end_offset=None means until end of `data`.
    # end_offset=-1 means conclude from the object header
    def loadFromBytes(self, data, begin_offset=0, end_offset=None):
        if end_offset == None: end_offset = len(data)
        offset = begin_offset
        Type = data[offset]
        Class = Type>>6
        Constructed = (Type&0b100000)!=0
        Tag = Type&0b11111
        offset += 1
        if Tag == 0b11111:
            curByte = 0x80
            Tag = 0
            while curByte&0x80:
                curByte = data[offset]
                Tag <<= 7
                Tag += (curByte & 0x7f)
                offset+=1
        self._loadType(Tag, Class, Constructed)
        Length = data[offset]
        offset+=1
        if Length&0x80:
            LengthOfLength = Length - 0x80
            if LengthOfLength == 0:
                raise Exception("Syntax Error (Length of Length = 0)")
            if LengthOfLength+offset>len(data):
                raise Exception("Error: not enough bytes for Length")
            Length = int.from_bytes(data[offset:offset+LengthOfLength], "big")
            offset+=LengthOfLength
        if ((end_offset != -1) and Length + offset > end_offset) or (Length + offset > len(data)):
            raise Exception("Error: not enough bytes for content")
        if (end_offset != -1) and Length + offset < end_offset:
            raise Exception("Error: redundent bytes")
        self._loadContentFromBytes(data, offset, Length)
        return Length+offset
    
    def _loadType(self, Tag, Class, Constructed):
        if (self.Tag != Tag): raise DERTypeError("Bad tag: (%d) instead of (%d)"%(Tag,self.Tag))
        if (self.Class != Class): raise DERTypeError("Bad class: (%d) instead class (%d)"%(Class,self.Class))
        if (self._Constructed != Constructed): raise DERTypeError("Bad Constructed: (%d) instead of (%d)"%(Constructed,self._Constructed))
        
    def _loadContentFromBytes(self,data,offset,Length):
        raise Exception("cannot load abstract type from bytes")
    
    def _getIndentedPrintable(self, indent, name):
        return " "*4*indent+("[%s]"%name if name else "")+"DERBase(Length: %s, Content: %s)"%(len(self.getContentOctets()),self.getContentOctets().encode("hex"))

class Primitive(DERBase):
    def __init__(self, Tag, Class, value:any=""):
        super().__init__(Tag,Class,False)
        assert (type(Tag)==int and type(Class)==int)
        self.setValue(value)

    def getContentOctets(self) -> bytes:
        return self._Content

    def setContentOctets(self, newContent: bytes):
        newVal = self._contentToValue(newContent)
        self._value = newVal
        self._Content = newContent

    def getValue(self):
        return self._value

    def setValue(self, newVal):
        newContent = self._valueToContent(newVal)
        self._value = newVal
        self._Content = newContent

    @property
    def value(self):
        return self.getValue()
    
    @value.setter
    def value(self, newVal):
        return self.setValue(newVal)
        
    def _valueToContent(self, value):
        return bytes.fromhex(value)
        
    def _contentToValue(self, content):
        return content.hex()

    def _getIndentedPrintable(self,indent,name):
        return " "*4*indent+("[%s]"%name if name else "") + self._reprLine()+"\n"
    
    def _reprLine(self):
        return "Primitive(Type: %s, Length: %s, Content: %s%s)"%(self.Tag,len(self.getContentOctets()),self.value[:100],"..." if (len(self.value)>100) else "")
    
    def _loadContentFromBytes(self, data:bytes, offset: int, Length:int):
        self.setContentOctets(data[offset:offset+Length])

class OctetString(Primitive):
    def __init__(self, value=""):
        super().__init__(OCTET_STRING_TAG_NUMBER, 0, value)
    
    def _getIndentedPrintable(self,indent,name):
        required_length = 4*indent+len("[%s]"%name if name else "") + len("OctetString()")+len(self._value)
        if required_length <= _get_console_width():
            val_repr = self._value
        else:
            missed = required_length - _get_console_width()
            val_repr = self._value[:max(0,len(self._value)-missed-3)]+"..."
        return " "*4*indent+("[%s]"%name if name else "") + "OctetString(%s)\n"%val_repr
        
    def _reprLine(self): # This is not really used, as _getIndentedPrintable is overridden
        return "OctetString(%s%s)"%(self.value[:100],"..." if (len(self.value)>100) else "")
    
class Null(Primitive):
    def __init__(self):
        super(Primitive,self).__init__(NULL_TAG_NUMBER,0,False)
        self._Content = b""
        self._wrappable = ["getContentOctets"]

    def _reprLine(self):
        return "NULL"
    
    def getValue(self):
        raise

    def setValue(self,newVal):
        raise

    def setContentOctets(self,newContent):
        assert (newContent == b"")

class Boolean(Primitive):
    def __init__(self, value:bool=False):
        super().__init__(BOOLEAN_TAG_NUMBER,0,value)

    def _valueToContent(self,value):
        if value == False:
            content = b"\x00"
        elif value == True:
            content = b"\x01"
        else:
            raise
        return content

    def _contentToValue(self,content):
        assert(len(content) == 1)
        return bool(content[0])

    def _reprLine(self):
        return "Integer(%d)"%(self._value)

class RestrictedCharacterString(Primitive):
    def __init__(self,value=b""):
        super().__init__(self.__class__.Tag, 0, value)

    def _valueToContent(self, value):
        return value

    def _contentToValue(self, content):
        return content

    def _reprLine(self):
        return "%s(\"%s\")"%(self.__class__.stringName,self._value)

class UTF8String(RestrictedCharacterString):
    Tag = 12
    stringName = "UTF8String"

class NumericString(RestrictedCharacterString):
    Tag = 18
    stringName = "NumericString"

class PrintableString(RestrictedCharacterString):
    Tag = 19
    stringName = "PrintableString"

class TeletexString(RestrictedCharacterString):
    Tag = 20
    stringName = "TeletexString"

class VideotexString(RestrictedCharacterString):
    Tag = 21
    stringName = "VideotexString"
    
class IA5String(RestrictedCharacterString):
    Tag = 22
    stringName = "IA5String"

class GraphicString(RestrictedCharacterString):
    Tag = 25
    stringName = "GraphicString"

class VisibleString(RestrictedCharacterString):
    Tag = 26
    stringName = "VisibleString"

class GeneralString(RestrictedCharacterString):
    Tag = 27
    stringName = "GeneralString"

class UniversalString(RestrictedCharacterString):
    Tag = 28
    stringName = "UniversalString"

class BMPString(RestrictedCharacterString):
    Tag = 30
    stringName = "BMPString"
    
class UTCTime(RestrictedCharacterString):
    Tag = 23
    stringName = "UTCTime"

class GeneralizedTime(RestrictedCharacterString):
    Tag = 24
    stringName = "GeneralizedTime"

class Integer(Primitive):
    def __init__(self, value=0):
        super().__init__(INTEGER_TAG_NUMBER, 0, value)

    def _valueToContent(self, value:int):
        if value == 0:
            content = b"\x00"
        elif value<0:
            byteLength = ((-value-1).bit_length()+8)//8 # the number of bits needed for (-x) is k ==> k=min(i) so that 2**(i-1)>=x ==> k = roundup(log(x))+1.
                                                       #roundup(log(x)) is numofbits(x-1). so number of bytes is ((numofbits(x-1)+1)+7)/8
            val2s = (value+(1<<(byteLength*8)))
            content = val2s.to_bytes(byteLength, "big")
        else:
            hexVal = "%x"%value
            content = bytes.fromhex("0"*(len(hexVal)%2)+hexVal)
            content = value.to_bytes((value.bit_length()+7)//8, "big")
            if content[0]>=0x80:
                content = b"\x00"+content
        return content

    def _contentToValue(self,content):
        if content[0]<0x80:
            return int.from_bytes(content, "big")
        else:
            return int.from_bytes(content, "big") - (1<<(8*len(content)))

    def _reprLine(self):
        return "Integer(%d)"%(self._value)

class BitString(Primitive):
    def __init__(self,value=""):
        super().__init__(BIT_STRING_TAG_NUMBER, 0, value)

    def _valueToContent(self, value):
        l = len(value)//8
        rem = len(value)%8
        pad = (8-rem)%8
        content = bytes([pad])
        for i in range(l):
            content+=bytes([int(value[i*8:i*8+8],2)])
        if rem:
            content+=bytes([int(value[-rem:]+"0"*pad,2)])
        return content

    def _contentToValue(self,content):
        pad = content[0]
        val = "".join(['{0:08b}'.format(content[i]) for i in range(1,len(content))])
        if pad: return val[:-pad]
        else: return val
        
    def _getIndentedPrintable(self,indent,name):
        required_length = 4*indent+len("[%s]"%name if name else "") + len("BitString()")+len(self._value)
        if required_length <= _get_console_width():
            val_repr = self._value
        else:
            missed = required_length - _get_console_width()
            val_repr = self._value[:max(0,len(self._value)-missed-3)]+"..."
        return " "*4*indent+("[%s]"%name if name else "") + "BitString(%s)\n"%val_repr
        
    def _reprLine(self): # This is not really used, as _getIndentedPrintable is overridden
        return "BitString(%s%s)"%(self._value[:100],"..." if (len(self._value)>100) else "")

class OID(Primitive):
    oids = {}
    def __init__(self, value:str="1.2"):
        super().__init__(OID_TAG_NUMBER,0,value)

    def _valueToContent(self, value:str):
        nums = list(map(int,value.split(".")))
        content = bytes([40*nums[0]+nums[1]])
        for n in nums[2:]:
            cur = bytes([(n&127)])
            n>>=7
            while n>0:
                cur+=bytes([0x80+(n&127)])
                n>>=7
            content+=cur[::-1]
        return content
    
    def _contentToValue(self, content:bytes):
        first = content[0]
        nums = [first/40,first%40]
        acc = 0
        i = 1
        while i < len(content):
            cur = content[i]
            acc+=cur&0x7F
            if cur & 0x80 == 0:
                nums.append(acc)
                acc = 0
            else:
                acc<<=7
            i+=1
        oidstr = ".".join(map(str,nums))
        if oidstr in OID.oids:
            return OID.oids[oidstr]
        else:
            return oidstr

    def _reprLine(self):
        return "OID(%s)"%(self.value)

class Choice(DERBase):
    def __init__(self, choices, selected = 0):
        choices = [(i,"") if isinstance(i, DERBase) else i for i in choices]
        self._choices = choices
        if type(selected) == int:
            # choose by index
            self._selected = self._choices[selected][0]
            self._selectedname = self._choices[selected][1]
        elif type(selected) == str:
            # choose by name
            x = [i for i in self._choices if i[1] == selected]
            assert (len(x)==1)
            self._selected = x[0][0]
            self._selectedname = x[0][1]
        else:
            # choose by der-object
            x = [i for i in self._choices if i[0] == selected]
            assert (len(x)==1)
            self._selected = x[0][0]
            self._selectedname = x[0][1]
        super(Choice,self).__init__(self._selected.Tag,self._selected.Class,self._selected._Constructed)

    def _getIndentedPrintable(self,indent,name):
        x = self._selected._getIndentedPrintable(indent,name)
        newLineIndex = x.find("\n")
        if newLineIndex == -1:
            return x+"<choice>"
        else:
            return x[:newLineIndex]+"<choice>"+x[newLineIndex:]
        
    def getEncoded(self):
        return self._selected.getEncoded()
    
    def __dir__(self):
        r = list(self.__dict__)
        if self._selectedname: r.append(self._selectedname)
        return r
    
    def __getattr__(self, attrName):
        for choice in self._choices:
            if choice[1]==attrName:
                return choice[0]
        raise AttributeError(attrName)
    
    def _loadType(self, Tag, Class, Constructed):
        for obj in self._choices:
            try:
                obj[0]._loadType(Tag,Class,Constructed)
            except DERTypeError:
                continue
            self._selected = obj[0]
            self._selectedname = obj[1]
            self.Tag = Tag
            self.Class = Class
            self._Constructed = Constructed
            return
        raise DERTypeError("No matching choice")
    
    def _loadContentFromBytes(self,data,offset,Length):
        self._selected._loadContentFromBytes(data,offset,Length)


class Tagged(DERBase):
    def __init__(self,Tag,Class,der,Constructed,optional=False):
        self.__dict__['_inner'] = der
        super(Tagged,self).__init__(Tag,Class,Constructed)
        self._optional=optional
        self._taggedType = ""
        self._presented = not optional

    def isOptional(self):
        return self._optional
    
    def isPresented(self):
        return self._presented
    
    def setPresented(self, val:bool):
        self._presented = val
    
    def _getIndentedPrintable(self,indent,name):
        if not self._presented:
            return indent*4*" "+"<[%s] optional and not presented>\n"%name
        x = self._inner._getIndentedPrintable(indent,name)
        newLineIndex = x.find("\n")
        if newLineIndex == -1:
            return x+"<%s Tagged(%d,%d)>"%(self._taggedType,self.Class,self.Tag)
        else:
            return x[:newLineIndex]+"<%s Tagged(%d,%d)>"%(self._taggedType,self.Class,self.Tag)+x[newLineIndex:]
    def getEncoded(self):
        raise
    
    def __dir__(self):
        r = list(self.__dict__)
        r+=self._inner._wrappable
        return r
    
    def getValue(self):
        return self._inner.getValue()

    def setValue(self, newVal):
        self._presented = True
        self._inner.setValue(newVal)

    def getContentOctets(self) -> bytes:
        return self._inner.getContentOctets()

    def setContentOctets(self, newContent: bytes):
        self._presented = True
        self._inner.setContentOctets(newContent)
    
    @property
    def value(self):
        return self.getValue()
    
    @value.setter
    def value(self, newVal):
        self._presented = True
        return self.setValue(newVal)
    
    def insert(self, index, item):
        self._presented = True
        self._inner.insert(index, item)

    def append(self, item):
        self._presented = True
        self._inner.append(item)
    
    def __getattr__(self,attrName):
        if attrName in self._inner._wrappable:
            return getattr(self._inner,attrName)
        else:
            raise AttributeError(attrName)
    def __setattr__(self,attrName,val):
        if attrName in self._inner._wrappable:
            self._inner.__setattr__(attrName,val)
        else:
            super(Tagged,self).__setattr__(attrName,val)

    def __getitem__(self,index):
        if "__getitem__" in self._inner._wrappable:
            return self._inner.__getitem__(index)
        
    def __setitem__(self,index,item):
        self._presented = True
        if "__setitem__" in self._inner._wrappable:
            self._inner.__setitem__(index,item)

    def __delitem__(self,index,item):
        if "__delitem__" in self._inner._wrappable:
            self._inner.__delitem__(index,item)

    def __len__(self):
        if "__len__" in self._inner._wrappable:
            return self._inner.__len__()
    
    def loadFromBytes(self, data, begin_offset=0, end_offset=None):
        try:
            self._presented = True
            return super().loadFromBytes(data, begin_offset, end_offset)
        except DERTypeError:
            if self._optional:
                self._presented = False
                return begin_offset
            else:
                raise

class ExplicitlyTagged(Tagged):
    def __init__(self,Tag,Class,der,optional=False):
        super(ExplicitlyTagged,self).__init__(Tag,Class,der,True,optional)
        self._taggedType = "Explicitly"

    def getEncoded(self):
        if not self._presented: return b""
        return Constructed(self.Tag,self.Class,contentObjects=[self._inner]).getEncoded()
    
    def _loadContentFromBytes(self, data, offset, Length):
        newOffset = self._inner.loadFromBytes(data, offset, offset+Length)
        assert(newOffset==offset+Length)

class ImplicitlyTagged(Tagged):
    def __init__(self,Tag,Class,der,optional=False):
        super(ImplicitlyTagged,self).__init__(Tag,Class,der,der._Constructed,optional)
        self._inner.Tag = Tag
        self._inner.Class = Class
        self._taggedType = "Implicitly"
    def getEncoded(self):
        if not self._presented: return b""
        return self._inner.getEncoded()
    def _loadContentFromBytes(self,data,offset,Length):
        self._inner._loadContentFromBytes(data,offset,Length)

class Constructed(DERBase):
    def __init__(self,Tag,Class,contentObjects=None):
        if contentObjects == None: contentObjects = []
        contentObjects = [(i,"") if isinstance(i,DERBase) else i for i in contentObjects]
        super(Constructed,self).__init__(Tag,Class,True)
        assert (type(Tag)==int and type(Class)==int)
        for obj in contentObjects: assert(isinstance(obj[0],DERBase))
        self._contentObjects = contentObjects
        self._update_wrappable()
        
    def _update_wrappable(self):
        self._wrappable = ["__getitem__","__setitem__","__delitem__","__len__","getContentOctets","insert","append"]+[i[1] for i in self._contentObjects if i[1]]

    def __dir__(self):
        r = super().__dir__()
        for o in self._contentObjects:
            if o[1]:
                r.append(o[1])
        return r

    def __getattr__(self,attrName):
        for obj in self._contentObjects:
            if obj[1]==attrName:
                return obj[0]
        raise AttributeError(attrName)
    
    def __setattr__(self,attrName,value):
        if attrName.startswith("_") or attrName not in self._wrappable: # contains the item elements (among other things)
            super(Constructed,self).__setattr__(attrName,value)
        else:
            raise Exception("Cannot change template")
    
    def __getitem__(self, index):
        return self._contentObjects[index][0]
    
    def __setitem__(self,index,item):
        assert(isinstance(item,DERBase))
        self._contentObjects[index][0]=item
        self._update_wrappable()

    def __delitem__(self,index):
        del self._contentObjects[index]
        self._update_wrappable()

    def insert(self, index, item):
        item = (item,"") if isinstance(item,DERBase) else item
        assert(isinstance(item[0],DERBase))
        self._contentObjects.insert(index,item)
        self._update_wrappable()

    def append(self, item):
        item = (item,"") if isinstance(item,DERBase) else item
        assert(isinstance(item[0],DERBase))
        self._contentObjects.append(item)
        self._update_wrappable()

    def __len__(self):
        return len(self._contentObjects)

    def getContentOctets(self) -> bytes:
        encContent = b""
        for i in self._contentObjects:
            encContent+=i[0].getEncoded()
        return encContent

    def _getIndentedPrintable(self,indent,name):
        res = ""
        res += " "*4*indent+("[%s]"%name if name else "") + self._reprLine()+"\n"
        if _maxPrintRecursion!=-1 and _maxPrintRecursion<=indent:
            if self._contentObjects:
                res += " "*4*(indent+1)+"... <%d items> ...\n"%len(self._contentObjects)
        else:
            for o in self._contentObjects:
                res+=o[0]._getIndentedPrintable(indent+1,o[1])
        return res
    
    def _reprLine(self):
        return "Constructed(Class=0x%x, Tag=0x%x):"%(self.Class,self.Tag)

class Sequence(Constructed):
    def __init__(self,contentObjects=None):
        super(Sequence,self).__init__(SEQUENCE_TAG_NUMBER,0,contentObjects)
    def _reprLine(self):
        return "Sequence:"
    def _loadContentFromBytes(self,data,offset,Length):
        orgOffset = offset
        for o in self._contentObjects:
            if offset == orgOffset+Length:
                assert isinstance(o[0], Tagged)
                assert o[0]._optional
                o[0]._presented = False
                continue
            offset = o[0].loadFromBytes(data, offset, -1)
        assert (orgOffset+Length == offset)

class SequenceOf(Sequence):
    def __init__(self,elementName:str,contentObjects=None, defaultTagging=None):
        super(SequenceOf,self).__init__(contentObjects)
        self.elementName = elementName
        self._defaultTagging = defaultTagging
    def _reprLine(self):
        if self.elementName.count("\n"):
            l1 = self.elementName.splitlines()[0]
            assert "{" in l1
            elementName = l1[:l1.find("{")+1] + "...}"
        else:
            elementName = self.elementName
        return "SequenceOf(%s):"%elementName
    def _loadContentFromBytes(self,data,offset,Length):
        self._contentObjects = []
        orgOffset = offset
        while offset < orgOffset+Length:
            o = buildTemplate(self.elementName, self._defaultTagging)
            offset = o.loadFromBytes(data, offset, -1)
            self._contentObjects.append((o,""))

class Set(Constructed):
    def __init__(self,contentObjects=None):
        super(Set,self).__init__(SET_TAG_NUMBER,0,contentObjects)
    def _reprLine(self):
        return "Set:"
    def _loadContentFromBytes(self,data,offset,Length):
        orgOffset = offset
        objs = self._contentObjects[:]
        while offset < orgOffset+Length:
            for o in objs:
                try:
                    offset = o[0].loadFromBytes(data, offset, -1)
                    objs.pop(o)
                    break
                except DERTypeError:
                    continue
            else:
                raise Exception("Error while loading Set")
        assert all([(isinstance(o, Tagged) and o.isOptional) for o in objs])
        assert (orgOffset+Length == offset)

class SetOf(Set):
    def __init__(self,elementName,contentObjects=None, defaultTagging = None):
        super(SetOf,self).__init__(contentObjects)
        self.elementName = elementName
        self._defaultTagging = defaultTagging
    def _reprLine(self):
        return "SetOf(%s):"%self.elementName
    def _loadContentFromBytes(self,data,offset,Length):
        self._contentObjects = []
        orgOffset = offset
        while offset < orgOffset+Length:
            o = buildTemplate(self.elementName, self._defaultTagging)
            offset = o.loadFromBytes(data, offset, -1)
            self._contentObjects.append((o,""))


class Any(DERBase):
    typesDict = {(0,INTEGER_TAG_NUMBER,False): Integer,
                 (0,BOOLEAN_TAG_NUMBER,False): Boolean,
                 (0,OCTET_STRING_TAG_NUMBER,False): OctetString,
                 (0,BIT_STRING_TAG_NUMBER,False): BitString,
                 (0,NULL_TAG_NUMBER,False): Null,
                 (0,OID_TAG_NUMBER,False): OID,
                 (0,UTF8STRING_TAG_NUMBER,False): UTF8String,
                 (0,NUMERICSTRING_TAG_NUMBER,False): NumericString,
                 (0,PRINTABLESTRING_TAG_NUMBER,False): PrintableString,
                 (0,TELETEXSTRING_TAG_NUMBER,False): TeletexString,
                 (0,VIDEOTEXSTRING_TAG_NUMBER,False): VideotexString,
                 (0,IA5STRING_TAG_NUMBER,False): IA5String,
                 (0,UTCTIME_TAG_NUMBER,False): UTCTime,
                 (0,GRAPHICSTRING_TAG_NUMBER,False): GraphicString,
                 (0,VISIBLESTRING_TAG_NUMBER,False): VisibleString,
                 (0,GENERALSTRING_TAG_NUMBER,False): GeneralString,
                 (0,UNIVERSALSTRING_TAG_NUMBER,False): UniversalString,
                 (0,BMPSTRING_TAG_NUMBER,False): BMPString,
                 (0,SEQUENCE_TAG_NUMBER,True): Sequence,
                 (0,SET_TAG_NUMBER,True): Set}
    def __init__(self, der=None):
        if not der: der = Null()
        super(Any,self).__init__(der.Tag,der.Class,der._Constructed)
        self._inner = der
    def _getIndentedPrintable(self,indent,name):
        x = self._inner._getIndentedPrintable(indent,name)
        newLineIndex = x.find("\n")
        if newLineIndex == -1:
            return x+"<any>"
        else:
            return x[:newLineIndex]+"<any>"+x[newLineIndex:]
    def getEncoded(self) -> bytes:
        return self._inner.getEncoded()
    
    def getValue(self):
        return self._inner.getValue()

    def setValue(self, newVal):
        self._inner.setValue(newVal)
    
    def getContentOctets(self) -> bytes:
        return self._inner.getContentOctets()

    def setContentOctets(self, newContent: bytes):
        self._inner.setContentOctets(newContent)
    
    @property
    def value(self):
        return self.getValue()
    
    @value.setter
    def value(self, newVal):
        self._presented = True
        return self.setValue(newVal)
    
    def __getattr__(self,attrName):
        if attrName in self._inner._wrappable:
            return getattr(self._inner,attrName)
        else:
            raise AttributeError(attrName)
        
    def __getitem__(self,index):
        return self._inner.__getitem__(index)
    
    def __setitem__(self,index,item):
        self._inner.__setitem__(index,item)

    def __delitem__(self,index):
        self._inner.__delitem__(index)

    def _loadType(self, Tag, Class, isConstructed):
        self.Tag = Tag
        self.Class = Class
        self._Constructed = isConstructed
        if (Class,Tag,isConstructed) in Any.typesDict:
            self._inner = Any.typesDict[(Class,Tag,isConstructed)]()
        elif isConstructed:
            self._inner = Constructed(Tag,Class)
        else:
            self._inner = Primitive(Tag,Class)
    def _loadContentFromBytes(self,data,offset,Length):
        if not self._Constructed:
            self._inner._loadContentFromBytes(data,offset,Length)
        else:
            orgOffset = offset
            while offset < orgOffset+Length:
                x = Any()
                offset = x.loadFromBytes(data, offset, -1)
                self._inner.append(x._inner)
            assert (offset == orgOffset+Length)

g_structures = {}
def loadStructuresDefs(data):
    data = data.replace("OBJECT IDENTIFIER","OBJECT_IDENTIFIER").replace("SEQUENCE OF","SEQUENCE_OF").replace("SET OF","SET_OF").replace("OCTET STRING","OCTET_STRING").replace("BIT STRING","BIT_STRING")
    ls = data.splitlines()
    i = 0
    while i<len(ls):
        l = ls[i].strip()
        if l == "":
            i+=1
            continue
        if not "::=" in l:
            print (i,l)
            raise
        name = l[:l.find("::=")].strip()
        
        if l.endswith("::="):
            i+=1
            l = ls[i].strip()
        else:
            l = l[l.find("::=")+3:].strip()
        structureDef = l
        if "{" in l and not "}" in l:
            while True:
                i+=1
                l = ls[i].strip()
                structureDef+="\n"+"    "+l
                if l.endswith("}"):
                    break
        i+=1
        if name in g_structures.keys():
            #print "overriding %s"%name
            pass
        g_structures[name] = structureDef
        
g_defaultTagging = None
def setDefaultTagging(defaultTagging):
    global g_defaultTagging
    g_defaultTagging = defaultTagging
    
def buildTemplate(name,defaultTagging = None):
    if defaultTagging == None:
        defaultTagging = g_defaultTagging
    bname=name
    if name.split()[0] in ["INTEGER","BOOLEAN","BIT_STRING","OCTET_STRING","OBJECT_IDENTIFIER","UTF8STRING","NUMERICSTRING","PRINTABLESTRING","TELETEXSTRING","VIDEOTEXSTRING","IA5STRING","UTCTime","GeneralizedTime","GRAPHICSTRING","VISIBLESTRING",\
                "GENERALSTRING","UNIVERSALSTRING","BMPSTRING","ANY","SEQUENCE","SET"] or name.startswith("SET_OF") or name.startswith("SEQUENCE_OF"):
        x = name
    else:
        x = g_structures[name]
    if x.startswith("INTEGER"):
        return Integer()
    elif x.startswith("BOOLEAN"):
        return Boolean()
    elif x.startswith("BIT_STRING"):
        return BitString()
    elif x.startswith("OCTET_STRING"):
        return OctetString()
    elif x.startswith("OBJECT_IDENTIFIER"):
        return OID()
    elif x.startswith("UTF8STRING"):
        return Utf8string()
    elif x.startswith("NUMERICSTRING"):
        return Numericstring()
    elif x.startswith("PRINTABLESTRING"):
        return Printablestring()
    elif x.startswith("TELETEXSTRING"):
        return Teletexstring()
    elif x.startswith("VIDEOTEXSTRING"):
        return Videotexstring()
    elif x.startswith("IA5STRING"):
        return Ia5string()
    elif x.startswith("UTCTime"):
        return UTCTime()
    elif x.startswith("GeneralizedTime"):
        return GeneralizedTime()
    elif x.startswith("GRAPHICSTRING"):
        return Graphicstring()
    elif x.startswith("VISIBLESTRING"):
        return Visiblestring()
    elif x.startswith("GENERALSTRING"):
        return Generalstring()
    elif x.startswith("UNIVERSALSTRING"):
        return Universalstring()
    elif x.startswith("BMPSTRING"):
        return Bmpstring()
    elif x.startswith("ANY"):
        return Any()
    elif x.startswith("CHOICE"):
        choices = []
        ls = x[x.find("{")+1:x.find("}")].split(",")
        for l in ls:
            l = l.replace(","," ").strip()
            name,l = l.split(None,1)
            tag = None
            if l.startswith("["):
                tag,l = l[1:].split("]",1)
                tag = int(tag)
                l = l.strip()
                if l.startswith("EXPLICIT"):
                    tagging = "E"
                    l = l.split(None,1)[1]
                elif l.startswith("IMPLICIT"):
                    tagging = "I"
                    l = l.split(None,1)[1]
                elif defaultTagging.upper() == "EXPLICIT":
                    tagging = "E"
                elif defaultTagging.upper() == "IMPLICIT":
                    tagging = "I"
                else:
                    raise Exception("No default tagging")
            else:
                tagging = None
            splited = l.split(None,1)
            typeName = splited[0]
            x = buildTemplate(typeName, defaultTagging)
            if tagging == "E":
                x = ExplicitlyTagged(tag, CONTEXT_SPECIFIC_CLASS,  x, False)
            elif tagging == "I":
                x = ImplicitlyTagged(tag if tag!=None else x.Tag, CONTEXT_SPECIFIC_CLASS if tag!=None else UNIVERSAL_CLASS, x, False)
            choices.append((x,name))
        return Choice(choices)
    
    elif x.startswith("SEQUENCE_OF"):
        return SequenceOf(x[len("SEQUENCE_OF")+1:], defaultTagging=defaultTagging)
    elif x.startswith("SET_OF"):
        return SetOf(x.split()[1], defaultTagging=defaultTagging)
    elif x.startswith("SEQUENCE") or x.startswith("SET"):
        objs = []
        ls = x[x.find("{")+1:x.find("}")].split(",")
        for l in ls:
            l = l.replace(","," ").strip()
            if l == "": continue
            name,l = l.split(None,1)
            tag = None
            if l.startswith("["):
                tag,l = l[1:].split("]",1)
                tag = int(tag)
                l = l.strip()
                if l.startswith("EXPLICIT"):
                    tagging = "E"
                    l = l.split(None,1)[1]
                elif l.startswith("IMPLICIT"):
                    tagging = "I"
                    l = l.split(None,1)[1]
                elif defaultTagging and defaultTagging.upper() == "EXPLICIT":
                    tagging = "E"
                elif defaultTagging and defaultTagging.upper() == "IMPLICIT":
                    tagging = "I"
                else:
                    raise Exception("No default tagging in %s"%bname)
            else:
                tagging = None
            splited = l.split(None,1)
            typeName = splited[0]
            if typeName in ["SEQUENCE_OF","SET_OF"]:
                typeName +=" "+splited[1]
                splited = splited[1:]
                
            l = splited[1] if len(splited)==2 else ""
            if l.startswith("OPTIONAL") or l.startswith("DEFAULT"):
                optional = True
            else:
                optional = False
            template = buildTemplate(typeName, defaultTagging)
            if tagging == "E":
                template = ExplicitlyTagged(tag, CONTEXT_SPECIFIC_CLASS,  template, optional)
            elif tagging == "I" or optional:
                template = ImplicitlyTagged(tag if tag!=None else template.Tag, CONTEXT_SPECIFIC_CLASS if tag!=None else UNIVERSAL_CLASS, template, optional)
            objs.append((template,name))
        if x.startswith("SEQUENCE"): return Sequence(objs)
        elif x.startswith("SET"): return Set(objs)
        else: raise
    elif x in g_structures.keys():
        return buildTemplate(x, defaultTagging)
    else:
        raise Exception("cannot build %s"%x)
