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

_maxPrintRecursion = -1
def setMaxPrintRecursion(num):
    global _maxPrintRecursion
    _maxPrintRecursion = num
    
class DERBase(object):
    def __init__(self,Tag,Class,Constructed,name=None):
        self._name=name
        self._wrappable = []
        self.Tag = Tag
        self.Class = Class
        self._Constructed = Constructed
    def __repr__(self):
        return self._getIndentedPrintable(0)
    def getName(self):
        return self._name
    def setName(self,name):
        self._name=name
    def getEncoded(self):
        encContent = self.getContentOctets()
        if self.Tag < 30:
            encType = chr((self.Class<<6)+self._Constructed*(1<<5)+(self.Tag))
        else:
            c = self.Tag
            r = chr(c&0x7f)
            c>>=7
            while c > 0:
                r += chr((c&0x7f)+0x80)
                c>>=7
                
            encType = chr((self.Class<<6)+self._Constructed*(1<<5)+0b11111)+r[::-1]
            
        contentLength=len(encContent)
        if contentLength < 0x80:
            encLength = chr(contentLength)
        else:
            r = ""
            c = contentLength
            while c >= 0x100:
                r += chr(c&0xff)
                c>>=8
            r+=chr(c)
            encLength = chr(0x80+len(r))+r[::-1]
        return encType+encLength+encContent
    def loadFromBytes(self,data,offset=0):
        begin_offset=offset
        Type = ord(data[offset])
        Class = Type>>6
        Constructed = (Type&0b100000)!=0
        Tag = Type&0b11111
        offset+=1
        if Tag == 0b11111:
            curByte = 0x80
            Tag = 0
            while curByte&0x80:
                curByte = ord(data[offset])
                Tag<<=7
                Tag+=(curByte&0b1111111)
                offset+=1
        self._loadType(Tag, Class, Constructed)
        Length = ord(data[offset])
        offset+=1
        if Length&0x80:
            LengthOfLength = Length - 0x80
            if LengthOfLength == 0:
                raise Exception("Syntax Error (Length of Length = 0)")
            if LengthOfLength+offset>len(data):
                raise Exception("Error: not enough bytes for Length")
            Length = int(data[offset:offset+LengthOfLength].encode("hex"),16)
            offset+=LengthOfLength
        if Length+offset>len(data):
            raise Exception("Error: not enough bytes for content")
        self._loadContentFromBytes(data,offset,Length)
        return Length+offset
    def _loadType(self, Tag, Class, Constructed):
        if (self.Tag != Tag): raise DERTypeError("Bad tag: (%d) instead of (%d)"%(Tag,self.Tag))
        if (self.Class != Class): raise DERTypeError("Bad class: (%d) instead class (%d)"%(Class,self.Class))
        if (self._Constructed != Constructed): raise DERTypeError("Bad Constructed: (%d) instead of (%d)"%(Constructed,self._Constructed))
        
    def _loadContentFromBytes(self,data,offset,Length):
        raise Exception("cannot load abstract type from bytes")
    def _getIndentedPrintable(self,indent):
        return " "*4*indent+"DERBase(Length: %s, Content: %s)"%(len(self.getContentOctets()),self.getContentOctets().encode("hex"))

class Primitive(DERBase):
    def __init__(self,Tag,Class,value="",name=None):
        super(Primitive,self).__init__(Tag,Class,False,name)
        assert (type(Tag)==int and type(Class)==int)
        self.setValue(value)
        self._wrappable = ["getContentOctets","setContentOctets","getValue","setValue","value"]

    def getContentOctets(self):
        return self._Content

    def setContentOctets(self,newContent):
        newVal = self._contentToValue(newContent)
        self._Value = newVal
        self._Content = newContent

    def getValue(self):
        return self._Value

    def setValue(self,newVal):
        newContent = self._valueToContent(newVal)
        self._Value = newVal
        self._Content = newContent

    def __getattr__(self,attrName):
        if attrName == "value":
            return self.getValue()
        else:
            raise AttributeError(attrName)
            
    def __setattr__(self,attrName,val):
        if attrName == "value":
            return self.setValue(val)
        else:
            super(Primitive,self).__setattr__(attrName,val)
        
    def _valueToContent(self,value):
        return value.decode("hex")
    def _contentToValue(self,content):
        return content.encode("hex")

    def _getIndentedPrintable(self,indent):
        return " "*4*indent+("[%s]"%self.getName() if self.getName() else "") + self._reprLine()+"\n"
    def _reprLine(self):
        return "Primitive(Type: %s, Length: %s, Content: %s%s)"%(self.Tag,len(self.getContentOctets()),self.value[:100],"..." if (len(self.value)>100) else "")
    def _loadContentFromBytes(self,data,offset,Length):
        self.setContentOctets(data[offset:offset+Length])

class OctetString(Primitive):
    def __init__(self,value="",name=None):
        super(OctetString,self).__init__(OCTET_STRING_TAG_NUMBER,0,value,name)
    def _reprLine(self):
        return "OctetString(%s%s)"%(self.value[:100],"..." if (len(self.value)>100) else "")
    
class Null(Primitive):
    def __init__(self,name=None):
        super(Primitive,self).__init__(NULL_TAG_NUMBER,0,False,name)
        self._Content = ""
        self._wrappable = ["getContentOctets"]
    def _reprLine(self):
        return "NULL"
    def getValue(self):
        raise
    def setValue(self,newVal):
        raise
    def setContentOctets(self,newContent):
        assert (newContent == "")

class Boolean(Primitive):
    def __init__(self,value=False,name=None):
        super(Boolean,self).__init__(BOOLEAN_TAG_NUMBER,0,value,name)
    def _valueToContent(self,value):
        if value == False:
            content = "\x00"
        elif value == True:
            content = "\x01"
        else:
            raise
        return content

    def _contentToValue(self,content):
        assert(len(content) == 1)
        return content[0]!="\x00"

    def _reprLine(self):
        return "Integer(%d)"%(self._Value)

class RestrictedCharacterString(Primitive):
    def __init__(self,value="",name=None):
        super(RestrictedCharacterString,self).__init__(self.__class__.Tag,0,value,name)

    def _valueToContent(self,value):
        return value

    def _contentToValue(self,content):
        return content

    def _reprLine(self):
        return "%s(\"%s\")"%(self.__class__.stringName,self._Value)

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
    def __init__(self,value=0,name=None):
        super(Integer,self).__init__(INTEGER_TAG_NUMBER,0,value,name)
    def _valueToContent(self,value):
        if value == 0:
            content = "\x00"
        elif value<0:
            byteLength = ((-value-1).bit_length()+8)/8 # the number of bits needed for (-x) is k ==> k=min(i) so that 2**(i-1)>=x ==> k = roundup(log(x))+1.
                                                       #roundup(log(x)) is numofbits(x-1). so number of bytes is ((numofbits(x-1)+1)+7)/8
            val2s = (value+(1<<(byteLength*8)))
            hexVal = "%x"%val2s
            content = ("0"*(len(hexVal)%2)+hexVal).decode("hex")
        else:
            hexVal = "%x"%value
            content = ("0"*(len(hexVal)%2)+hexVal).decode("hex")
            if ord(content[0])>=0x80:
                content = "\x00"+content
        return content

    def _contentToValue(self,content):
        if ord(content[0])<0x80:
            return int(content.encode("hex"),16)
        else:
            return int(content.encode("hex"),16) - (1<<(8*len(content)))

    def _reprLine(self):
        return "Integer(%d)"%(self._Value)

class BitString(Primitive):
    def __init__(self,value="",name=None):
        super(BitString,self).__init__(BIT_STRING_TAG_NUMBER,0,value,name)
    def _valueToContent(self,value):
        l = len(value)/8
        rem = len(value)%8
        pad = (8-rem)%8
        content = chr(pad)
        for i in xrange(l):
            content+=chr(int(value[i*8:i*8+8],2))
        if rem:
            content+=chr(int(value[-rem:]+"0"*pad,2))
        return content

    def _contentToValue(self,content):
        pad = ord(content[0])
        val = "".join(['{0:08b}'.format(ord(content[i])) for i in xrange(1,len(content))])
        if pad: return val[:-pad]
        else: return val

    def _reprLine(self):
        return "BitString(%s%s)"%(self._Value[:100],"..." if (len(self._Value)>100) else "")

class OID(Primitive):
    oids = {}
    def __init__(self,value="1.2",name=None):
        super(OID,self).__init__(OID_TAG_NUMBER,0,value,name)
    def _valueToContent(self,value):
        nums = map(int,value.split("."))
        content = chr(40*nums[0]+nums[1])
        for n in nums[2:]:
            cur = chr((n&127))
            n>>=7
            while n>0:
                cur+=chr(0x80+(n&127))
                n>>=7
            content+=cur[::-1]
        return content
    def _contentToValue(self,content):
        first = ord(content[0])
        nums = [first/40,first%40]
        acc = 0
        i = 1
        while i < len(content):
            cur = ord(content[i])
            acc+=cur&0x7F
            if cur & 0x80 == 0:
                nums.append(acc)
                acc = 0
            else:
                acc<<=7
            i+=1
        oidstr = ".".join(map(str,nums))
        if oidstr in OID.oids:
            return oids[oidstr]
        else:
            return oidstr

    def _reprLine(self):
        return "OID(%s)"%(self.value)


class Choice(DERBase):
    def __init__(self, choices, selected = 0,name=None):
        self._choices = choices
        if type(selected) == int:
            self._selected = self._choices[selected]
        else:
            assert(isinstance(selected,DERBase))
            assert(selected in choices)
            self._selected = selected
        super(Choice,self).__init__(self._selected.Tag,self._selected.Class,self._selected._Constructed,name)
    def _getIndentedPrintable(self,indent):
        x = self._selected._getIndentedPrintable(indent)
        if self._name:
            x = x[:x.find("[")+1]+"%s."%self._name+x[x.find("[")+1:]
        newLineIndex = x.find("\n")
        if newLineIndex == -1:
            return x+"<choice>"
        else:
            return x[:newLineIndex]+"<choice>"+x[newLineIndex:]
    def getEncoded(self):
        return self._selected.getEncoded()
    def __dir__(self):
        r = list(self.__dict__)
        if self._selected.getName(): r.append(self._selected.getName())
        return r
    def __getattr__(self,attrName):
        for obj in self._choices:
            if obj.getName()==attrName:
                return obj
        raise AttributeError(attrName)
    def _loadType(self, Tag, Class, Constructed):
        for obj in self._choices:
            try:
                obj._loadType(Tag,Class,Constructed)
            except DERTypeError:
                continue
            self._selected = obj
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
        self._presented = True
    def isOptional(self):
        return self._optional
    def getName(self):
        return self._inner.getName()
    def setName(self,name):
        self._inner.setName(Name)
    def _getIndentedPrintable(self,indent):
        if not self._presented:
            return indent*4*" "+"<[%s] optional and not presented>\n"%self._inner.getName()
        x = self._inner._getIndentedPrintable(indent)
        newLineIndex = x.find("\n")
        if newLineIndex == -1:
            return x+"<%s Tagged(%d,%d)>"%(self._taggedType,self.Class,self.Tag)
        else:
            return x[:newLineIndex]+"<%s Tagged(%d,%d)>"%(self._taggedType,self.Class,self.Tag)+x[newLineIndex:]
    def getEncoded(self):
        raise

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
        if "__setitem__" in self._inner._wrappable:
            self._inner.__setitem__(index,item)

    def __delitem__(self,index,item):
        if "__delitem__" in self._inner._wrappable:
            self._inner.__delitem__(index,item)

    def __len__(self):
        if "__len__" in self._inner._wrappable:
            return self._inner.__len__()
    def loadFromBytes(self,data,offset=0):
        savedOffset = offset
        try:
            self._presented = True
            return super(Tagged,self).loadFromBytes(data,offset)
        except DERTypeError:
            if self._optional:
                self._presented = False
                return savedOffset
            else:
                raise
class ExplicitlyTagged(Tagged):
    def __init__(self,Tag,Class,der,optional=False):
        super(ExplicitlyTagged,self).__init__(Tag,Class,der,True,optional)
        self._taggedType = "Explicitly"
    def getEncoded(self):
        if not self._presented: return ""
        return Constructed(self.Tag,self.Class,contentObjects=[self._inner]).getEncoded()
    def _loadContentFromBytes(self,data,offset,Length):
        newOffset = self._inner.loadFromBytes(data,offset)
        assert(newOffset==offset+Length)

class ImplicitlyTagged(Tagged):
    def __init__(self,Tag,Class,der,optional=False):
        super(ImplicitlyTagged,self).__init__(Tag,Class,der,der._Constructed,optional)
        self._inner.Tag = Tag
        self._inner.Class = Class
        self._taggedType = "Implicitly"
    def getEncoded(self):
        if not self._presented: return ""
        return self._inner.getEncoded()
    def _loadContentFromBytes(self,data,offset,Length):
        self._inner._loadContentFromBytes(data,offset,Length)



class Constructed(DERBase):
    def __init__(self,Tag,Class,contentObjects=None,name=None):
        if contentObjects == None: contentObjects = []
        super(Constructed,self).__init__(Tag,Class,True,name)
        assert (type(Tag)==int and type(Class)==int)
        for obj in contentObjects: assert(isinstance(obj,DERBase))
        self.contentObjects = contentObjects
        self._wrappable = ["__getitem__","__setitem__","__delitem__","__len__","getContentOctets","insert","append"]

    def __dir__(self):
        r = list(self.__dict__)
        for o in self.contentObjects:
            if o.getName():
                r.append(o.getName())
        return r

    def __getattr__(self,attrName):
        for obj in self.contentObjects:
            if obj.getName()==attrName:
                return obj
        raise AttributeError(attrName)
    
    def __getitem__(self,index):
        return self.contentObjects[index]
    
    def __setitem__(self,index,item):
        assert(isinstance(item,DERBase))
        self.contentObjects[index]=item

    def __delitem__(self,index):
        del self.contentObjects[index]

    def insert(self,index,item):
        self.contentObjects.insert(index,item)

    def append(self,item):
        self.contentObjects.append(item)

    def __len__(self):
        return len(self.contentObjects)

    def getContentOctets(self):
        encContent = ""
        for i in self.contentObjects:
            encContent+=i.getEncoded()
        return encContent

    def _getIndentedPrintable(self,indent):
        res = ""
        res += " "*4*indent+("[%s]"%self.getName() if self.getName() else "") + self._reprLine()+"\n"
        if _maxPrintRecursion!=-1 and _maxPrintRecursion<=indent:
            if self.contentObjects:
                res += " "*4*(indent+1)+"... <%d items> ...\n"%len(self.contentObjects)
        else:
            for o in self.contentObjects:
                res+=o._getIndentedPrintable(indent+1)
        return res
    def _reprLine(self):
        return "Constructed(Class=0x%x, Tag=0x%x):"%(self.Class,self.Tag)

class Sequence(Constructed):
    def __init__(self,contentObjects=None,name=None):
        super(Sequence,self).__init__(SEQUENCE_TAG_NUMBER,0,contentObjects,name)
    def _reprLine(self):
        return "Sequence:"
    def _loadContentFromBytes(self,data,offset,Length):
        orgOffset = offset
        for o in self.contentObjects:
            offset = o.loadFromBytes(data,offset)
        assert (orgOffset+Length == offset)

class SequenceOf(Sequence):
    def __init__(self,elementName,contentObjects=None,name=None):
        super(SequenceOf,self).__init__(contentObjects,name)
        self.elementName = elementName
    def _reprLine(self):
        return "SequenceOf(%s):"%self.elementName
    def _loadContentFromBytes(self,data,offset,Length):
        self.contentObjects = []
        orgOffset = offset
        while offset < orgOffset+Length:
            o = buildTemplate(self.elementName)
            offset = o.loadFromBytes(data,offset)
            self.contentObjects.append(o)

class Set(Constructed):
    def __init__(self,contentObjects=None,name=None):
        super(Set,self).__init__(SET_TAG_NUMBER,0,contentObjects,name)
    def _reprLine(self):
        return "Set:"
    def _loadContentFromBytes(self,data,offset,Length):
        orgOffset = offset
        objs = self.contentObjects[:]
        while offset < orgOffset+Length:
            for o in objs:
                try:
                    offset = o.loadFromBytes(data,offset)
                    objs.pop(o)
                    break
                except DERTypeError:
                    continue
        assert all([(isinstance(o, Tagged) and o.isOptional) for o in objs])
        assert (orgOffset+Length == offset)

class SetOf(Set):
    def __init__(self,elementName,contentObjects=None,name=None):
        super(SetOf,self).__init__(contentObjects,name)
        self.elementName = elementName
    def _reprLine(self):
        return "SetOf(%s):"%self.elementName
    def _loadContentFromBytes(self,data,offset,Length):
        self.contentObjects = []
        orgOffset = offset
        while offset < orgOffset+Length:
            o = buildTemplate(self.elementName)
            offset = o.loadFromBytes(data,offset)
            self.contentObjects.append(o)


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
    def __init__(self, der=None, name=None):
        if not der: der = Null()
        super(Any,self).__init__(der.Tag,der.Class,der._Constructed,name)
        self._inner = der
    def _getIndentedPrintable(self,indent):
        x = self._inner._getIndentedPrintable(indent)
        if self.getName():
            nameIndex = len(x) - len(x.lstrip())
            x = x[:nameIndex]+"[%s]"%self.getName()+x[nameIndex:]
        newLineIndex = x.find("\n")
        if newLineIndex == -1:
            return x+"<any>"
        else:
            return x[:newLineIndex]+"<any>"+x[newLineIndex:]
    def getEncoded(self):
        return self._inner.getEncoded()
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
            self._inner = Any.typesDict[(Class,Tag,isConstructed)](name=self.getName())
        elif isConstructed:
            self._inner = Constructed(Tag,Class,name=self.getName())
        else:
            self._inner = Primitive(Tag,Class,name = self.getName())
    def _loadContentFromBytes(self,data,offset,Length):
        if not self._Constructed:
            self._inner._loadContentFromBytes(data,offset,Length)
        else:
            orgOffset = offset
            while offset < orgOffset+Length:
                x = Any()
                offset = x.loadFromBytes(data,offset)
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
            print i,l
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
        

def buildTemplate(name,defaultTagging = None):
    bname=name
    if name in ["INTEGER","BOOLEAN","BIT_STRING","OCTET_STRING","OBJECT_IDENTIFIER","UTF8STRING","NUMERICSTRING","PRINTABLESTRING","TELETEXSTRING","VIDEOTEXSTRING","IA5STRING","UTCTime","GeneralizedTime","GRAPHICSTRING","VISIBLESTRING",\
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
            x = buildTemplate(typeName)
            x.setName(name)
            if tagging == "E":
                x = ExplicitlyTagged(tag, CONTEXT_SPECIFIC_CLASS,  x, False)
            elif tagging == "I":
                x = ImplicitlyTagged(tag if tag!=None else x.Tag, CONTEXT_SPECIFIC_CLASS if tag!=None else UNIVERSAL_CLASS, x, False)
            choices.append(x)
        return Choice(choices)
    
    elif x.startswith("SEQUENCE_OF"):
        return SequenceOf(x.split()[1])
    elif x.startswith("SET_OF"):
        return SetOf(x.split()[1])
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
            template = buildTemplate(typeName)
            template.setName(name)
            if tagging == "E":
                template = ExplicitlyTagged(tag, CONTEXT_SPECIFIC_CLASS,  template, optional)
            elif tagging == "I" or optional:
                template = ImplicitlyTagged(tag if tag!=None else template.Tag, CONTEXT_SPECIFIC_CLASS if tag!=None else UNIVERSAL_CLASS, template, optional)
            objs.append(template)
        if x.startswith("SEQUENCE"): return Sequence(objs)
        elif x.startswith("SET"): return Set(objs)
        else: raise
    elif x in g_structures.keys():
        return buildTemplate(x)
    else:
        raise Exception("cannot build %s"%x)
