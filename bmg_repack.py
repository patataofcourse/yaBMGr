import binascii

VERSION = "v1"

filename = input("File name? ") #TODO: it should be an argparse
if filename == "":
    filename = "data.Msg/bmg_out/tmd_mainroom_msg_JP.rbmg"
file = open(filename, "r").read()

def binify(dict, *args, **kwargs):
    dict_bin = b''
    for argn in args:
        arg = dict[argn]
        if type(arg) == bytes:
            dict_bin += arg
        elif type(arg) == int:
            dict_bin += arg.to_bytes(kwargs.get(argn, 4), kwargs.get(argn+"_encoding", "little")) #Only little endian allowed here >:(
        elif type(arg) == tuple or type(arg) == list:
            c = 0
            length = kwargs.get(argn, 4)
            enc = kwargs.get(f"{argn}_encoding", "little")
            for item in arg:
                if type(item) == bytes:
                    dict_bin += item
                elif type(item) == int:
                    dict_bin += item.to_bytes(kwargs.get(argn+str(c), length), kwargs.get(f"{argn}{c}_encoding", enc)) #Only little endian allowed here >:(
                else:
                    raise TypeError("tuples or lists in binify() can only contain ints or bytes")
                c += 1
        else:
            raise TypeError(f"binify() argument must be int, tuple, list, or bytes ({argn} is {type(arg)})")
    return dict_bin

def encode_string(string):
    out = b''
    slash = False
    pos = 0
    while True:
        if pos >= len(string):
            break
        char = string[pos]

        if slash:
            slash = False
            if char == "\\":
                out += char.encode("UTF-16LE") #LE encoding haha see what i did there?
                pos += 1
                continue
            elif char == "e":
                content = string[pos+2:].split(">")[0].replace(" ", "")
                content_bytes = int("0x"+content,0).to_bytes(len(content)//2, "big")
                size = len(content)//2 + 3
                binsize = size.to_bytes(1, "little")
                out += b"\x1a\x00" + binsize + content_bytes
                pos += len(content) + 5
                continue
            elif char == "z":
                bin = bytes([int("0x"+string[pos+2:pos+4], 0)]) + bytes([int("0x"+string[pos+4:pos+6], 0)])
                out += bin
                pos += 7
                continue
        if char == "\\":
            slash = True
            pos += 1
            continue
        pos += 1
        out += char.encode("UTF-16LE") #LE encoding haha see what i did there?
    return out + b"\x00\x00"

#exclude comments
lines = []
messages = False
for line in file.split("\n"):
    if line.startswith("#"):
        continue
    if line.startswith("@MESSAGES"):
        messages = True
    if line == "":
        continue
    if not (messages and line.startswith("    ")):
        lines.append(line.split("#")[0].rstrip())
    else:
        lines.append(line)

header = "\n".join(lines).split("@MESSAGES")[0].rstrip().split("\n")
messages = "\n".join("\n".join(lines).split("@MESSAGES")[1].split("\n")[1:]).split("\n")

#header
HEADER_SIZE = 0x20
head = {
    "MAGIC": b'MESGbmg1',
    "size": 0, #will be set later
    "num_blocks": 2
}
info = {
    "MAGIC": b'INF1'
}
data = {
    "MAGIC": b'DAT1'
}
msg_ids = {
    "MAGIC": b'MID1'
}


for line in header:
    line = line.split("=")
    if line[0].rstrip() == "mid_exists":
        if line[1].lstrip() == "1":
            head["num_blocks"] = 3
    elif line[0].rstrip() in ("encoding", "reserved"):
        head[line[0].rstrip()] = int(line[1].lstrip(), 0)
    elif line[0].rstrip() in ("reserved_inf", "reserved_mid"):
        items = eval(line[1].rstrip())
        out = []
        for item in items:
            out.append(item)
        if line[0].rstrip() == "reserved_inf":
            info["reserved"] = out
        else:
            msg_ids["reserved"] = out
    elif line[0].rstrip() == "entry_size":
        info["entry_size"] = int(line[1].lstrip(), 0)
    else:
        raise Exception(f"Header has an unknown variable: {line[0].rstrip()}")

if head["encoding"] != 2:
    raise Exception("Only UTF-16 (encoding 2) supported!")

indented = True
ids = []
msg = b''
offsets = []
parameters = []
curr_msg = {"id":None, "param":None, "text":""}
for line in messages:
    if indented and line.startswith("    "):
        curr_msg["text"] += "\n" + line[4:]
    elif indented:
        indented = False
        if curr_msg["id"] != None:
            ids.append(curr_msg["id"])
            parameters.append(curr_msg["param"])
            offsets.append(len(msg))
            msg += encode_string(curr_msg["text"])
        curr_msg["id"] = int(line.split(" ")[0])
        param = eval(" ".join(line.split(" ")[1:]))
        param.reverse()
        param = bytes(param)
        curr_msg["param"] = param
    else:
        if not line.startswith("    "):
            raise Exception(f"Next line should be indented! (message {curr_msg['id']})")
        curr_msg["text"] = line[4:]
        indented = True
ids.append(curr_msg["id"])
parameters.append(curr_msg["param"])
offsets.append(len(msg))
msg += encode_string(curr_msg["text"])

msg_ids["ids"] = ids
data["string_pool"] = msg
entries = []
c = 0
for offset in offsets: #extra step, but it makes printing stuff easier
    entries.append(offset.to_bytes(4, "little")+parameters[c])
    c += 1
info["message_entry"] = entries
info["num_entries"] = len(entries)
msg_ids["num_entries"] = len(entries)

info["size"] = info["num_entries"]*info["entry_size"] + 0x10
data["size"] = len(data["string_pool"]) + 8
msg_ids["size"] = msg_ids["num_entries"]*4 + 0x10
head["size"] = 0x20 + info["size"] + data["size"]
if head["num_blocks"] == 3: #only applies until we add more sections
    head["size"] += msg_ids["size"]

header_bin = binify(head, "MAGIC", "size", "num_blocks", "encoding", "reserved", encoding=1, reserved=15, reserved_encoding="big")
info_bin = binify(info, "MAGIC", "size", "num_entries", "entry_size", "reserved", "message_entry", num_entries=2, entry_size=2, reserved=1, reserved0=2)
data_bin = binify(data, "MAGIC", "size", "string_pool")
mid_bin = binify(msg_ids, "MAGIC", "size", "num_entries", "reserved", "ids", num_entries=2, reserved=1, reserved2=4, reserved2_encoding="big")

if filename.endswith(".rbmg"): #TODO: this should only be the default
    outfile = filename[:-5] + ".bmg"
else:
    outfile = filename + ".bmg"
outfile = open(outfile, "wb")
outfile.write(header_bin)
outfile.write(info_bin)
outfile.write(data_bin)
if head["num_blocks"] == 3: #only applies until we add more sections
    outfile.write(mid_bin)
outfile.close()