#NOT AN ACTUAL PYTHON FILE! only called .py for the syntax coloring

header = { #32 bytes
    signature,  #Always "MESG"
    data_type,  #Always "bmg1"
    data_size,  #Filesize (4 bytes)
    num_blocks, #Number of sections (4 bytes), usually is 3 or 2
    charset,    #Encoding (1 byte)
    reserved0,  #Unknown (1 byte)
    reserved1,  #Unknown (2 bytes)
    reserved,   #Unknown (8 bytes)
    user_work   #Unknown (4 bytes)
}
info = {
    kind,                     #Always "INF1"
    size,                     #Section length (4 bytes)
    num_entries,              #Number of messages (2 bytes)
    entry_size,               #The length of each item (2 bytes), usually 8
    group_ID,                 #BMG file ID (2 bytes)
    default_color,            #"default color index" (1 byte)
    reserved,                 #Unknown (1 byte)
    message_entry = [         #num_entries items
        (offset, attributes), #each item is entry_size long, with offset being 4 bytes long
        (offset, attributes),
        ...
    ]
}
data = {
    kind,       #Always "DAT1"
    size,       #Section length (4 bytes)
    string_pool #The entirety of the string pool, to be separated later
}
message_ids = {
    kind,                  #Always "MID1"
    size,                  #Section length (4 bytes)
    num_entries,           #Same as info.num_entries (2 bytes)
    format,                #Unknown (1 byte)
    info,                  #Unknown (1 byte)
    reserved,              #Unknown (4 bytes)
    ids = [                #num_entries items
        id1, id2, id3, ... #each ID is 4 bytes long
    ]
}

Managing the string pool:
- 0x0000 -> end of file, unless in an escape sequence
- 0x001A -> escape sequence:
    * offset 0x00 -> 0x001A
    * offset 0x02 -> xx (size in bytes of sequence)
    * offset 0x03 -> yy zzzz (message tag ID?)
    Decompile to \e{xx yy zzzz ????}