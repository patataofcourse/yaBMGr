import binascii

VERSION = "v1" #make sure to update this too!

def unpack(infile, outfile):
    file = open(infile, "rb").read()
    header = read_header(file[:0x20]) #Always is 0x20 bytes long

    unread_data = file[0x20:]
    info = None
    data = None
    msg_ids = None
    for section in range(header["num_sections"]):
        size = int.from_bytes(unread_data[4:8], "little")
        stype = unread_data[:4].decode("ASCII")
        content = unread_data[8:size]
        if stype == "INF1":
            if info != None:
                raise Exception("more than one INF1 section!")
            info = {
            "num_entries": int.from_bytes(content[:2], "little"), #has to correspond with MID1{"num_entries"}
            "entry_size": int.from_bytes(content[2:4], "little"),
            "group_id": int.from_bytes(content[4:6], "little"),
            "default_color": content[6],
            "reserved": content[7],
            "message_entry": []
            }
            content = content[8:]
            for entry in range(info["num_entries"]):
                entry = content[0:info["entry_size"]]
                info["message_entry"].append( (int.from_bytes(entry[:4], "little"), entry[4:]) )
                content = content[info["entry_size"]:]
        elif stype == "MID1":
            if msg_ids != None:
                raise Exception("more than one MID1 section!")
            msg_ids = {
                "num_entries": int.from_bytes(content[:2], "little"), #has to correspond with INF1{"num_entries"}
                "format": content[2],
                "info": content[3],
                "reserved": content[4:8],
                "reserved_text": "0x" + binascii.hexlify(content[4:8]).decode("ascii"),
                "ids": []
            }
            content = content[8:]
            for entry in range(msg_ids["num_entries"]):
                msg_ids["ids"].append(int.from_bytes(content[:4], "little"))
                content = content[4:]            
        elif stype == "DAT1":
            if data != None:
                raise Exception("more than one DAT1 section!")
            data = content
        else:
            raise Exception(f"unsupported section kind: {stype}")
        unread_data = unread_data[size:]

    if info == None:
        raise Exception("INF1 section missing!")
    if data == None:
        raise Exception("DAT1 section missing!")

    messages = []
    for entry in info["message_entry"]:
        msg = export_string(data, entry[0])
        if entry[1] == b'':
            param = None
        else:
            param = bytearray(entry[1])
            param.reverse()
            param = list(param)
        messages.append((msg, param))

    if msg_ids != None:
        if msg_ids["num_entries"] != info["num_entries"]:
            raise Exception("num_entries doesn't match between the INF1 and MID1")
        ids = msg_ids["ids"]
    else:
        ids = range(len(messages))

    #Here's where we make the actual file
    out = f'''
#Readable BMG file exported by patataofcourse's yaBMGr {VERSION}
entry_size = {info["entry_size"]}
encoding = {header["encoding"]} #{header["encoding_name"]}
mid_exists = {0 if msg_ids == None else 1}
reserved = {header["reserved_text"]}
reserved_inf = ({info["group_id"]}, {info["default_color"]}, {info["reserved"]})
'''.lstrip("\n")
    if msg_ids != None:
        out += f'''reserved_mid = ({msg_ids["format"]}, {msg_ids["info"]}, {msg_ids["reserved_text"]})\n'''

    out += "\n@MESSAGES\n"

    c = 0
    for message in messages:
        out += f"{ids[c]} {repr(message[1])}\n"
        for line in message[0].split("\n"):
            out += "    " + line + "\n"
        c += 1
    
    if outfile == None:
        if infile.endswith(".bmg"): #TODO: this should only be the default
            outfile = infile[:-4] + ".rbmg"
        else:
            outfile = infile + ".rbmg"
    outfile = open(outfile, "w", encoding="utf-8")
    outfile.write(out)
    outfile.close()

def read_header(header):
    out = {}

    if header[:8] != b"MESGbmg1": #These are always set to this in BMG
        raise Exception("not a valid BMG file!")

    out["size"] = int.from_bytes(header[8:0xc], "little") #Only little endian supported atm

    out["num_sections"] = int.from_bytes(header[0xc:0x10], "little") #Only little endian supported atm

    encoding = header[0x10]
    encoding_name = ["Legacy", "CP1252", "UTF-16", "Shift-JIS", "UTF-8"][encoding]
    if encoding not in (2,):
        raise Exception(f"Encoding {encoding} ({encoding_name}) not supported yet!") #Only UTF-16 supported atm
    out["encoding"] = encoding
    out["encoding_name"] = encoding_name

    out["reserved"] = header[0x11:]
    out["reserved_text"] = '0x'+binascii.hexlify(out['reserved']).decode('ASCII') #hex representation of the reserved field

    return out

def export_string(pool, pos):
    out = ""
    def hex_(val):
        return binascii.hexlify(bytes([val])).decode('ascii')

    while True:
        if pos % 2 == 1: #'cause UTF-16
            pos += 1
            continue

        if pool[pos:pos+2] == b'\x00\x00': #NULL
            break

        if pool[pos:pos+2] == b'\x1a\x00': #Escape character
            extra = binascii.hexlify(pool[pos+6:pos+pool[pos+2]], sep=" ", bytes_per_sep=2).decode('ascii')
            out += f"\\e<{hex_(pool[pos+3])} {hex_(pool[pos+4])}{hex_(pool[pos+5])}{' ' if extra != '' else ''}{extra}>" #"\e<xx yyzz ...>"
            pos += pool[pos+2]
            continue
        
        u = int.from_bytes(pool[pos:pos+2], "little")
        if u >= 0xd800 and u <= 0xdfff: #because it errors in tmd_talk_msg_JP.bmg
            out += f"\z<{binascii.hexlify(pool[pos:pos+2]).decode('ascii')}>"
            pos += 1
            print(f"WARNING: invalid character {pool[pos:pos+2]}")
            continue
        del u
        
        out += pool[pos:pos+2].decode("UTF-16LE") #Le encoding
        pos += 1
    return out

if __name__ == "__main__":
    unpack(input("Input file? "), input("Output file? "))