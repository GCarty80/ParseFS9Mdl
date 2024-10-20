import os
import json

mdl_dir_to_parse = "D:\\Flight\\FSX\\SimObjects\\Airplanes\\HJG Boeing KC-135A Early v6.1 BETA\\model.KC-135A_Early"

var_type_from_number = {1:["FLOAT32",4], 2:["UINT32",4], 4:["UINT16",2], 6:["FLAGS16",2], 7:["SINT16",2]}

with open("fs2004_vars.json") as f:
    fs2004_vars_dict = json.load(f)

class BadBlockException(Exception):
    pass

bgl_record_types = {0x06:["BGL_SPNT",
                            [("x","SINT16"),
                             ("y","SINT16"),
                             ("z","SINT16")]
                         ],
                    0x07:["BGL_CPNT",
                            [("x","SINT16"),
                             ("y","SINT16"),
                             ("z","SINT16")]
                         ],
                    0x08:["BGL_CLOSURE",[]],
                    0x0d:["BGL_JUMP",
                            [("displacement","SINT16")]
                         ],
                    0x22:["BGL_RETURN",[]],
                    0x23:["BGL_CALL",
                            [("displacement","SINT16")]
                         ],
                    0x34:["BGL_SUPER_SCALE",
                            [("jump_if_fail","SINT16"),
                             ("view_range","UINT16"),
                             ("model_size","UINT16"),
                             ("super_scale","UINT16")]
                         ],
                    0x39:["BGL_IFMASK",
                            [("jump_if_fail","SINT16"),
                             ("var","VAR16"),
                             ("mask","VAR16")]
                         ],
                    0x3a:["BGL_VPOSITION",
                            [("jump_if_fail","SINT16"),
                             ("view_range","UINT16"),
                             ("model_size","UINT16"),
                             ("index","ZERO2"),
                             ("LATLONGLAT_offset","VAR16")]
                         ],
                    0x3b:["BGL_VINSTANCE",
                            [("offset","SINT16"),
                             ("call","VAR16")]
                         ],
                    0x40:["BGL_SHADOW_VPOSITION",
                            [("jump_if_fail","SINT16"),
                             ("view_range","UINT16"),
                             ("model_size","UINT16"),
                             ("index","ZERO2"),
                             ("LATLONGLAT_offset","VAR16")]
                         ],
                    0x88:["BGL_JUMP32",
                            [("displacement","SINT32")]
                         ],
                    0x8e:["BGL_VFILE_MARKER",
                            [("offset","SINT16")]
                         ]
                    }
    
def makeGuid(input_bytes):
    return "%08X-%04X-%04X-%04X-%012X"%(int.from_bytes(input_bytes[:4], "little"), int.from_bytes(input_bytes[4:6], "little"), int.from_bytes(input_bytes[6:8], "little"), int.from_bytes(input_bytes[8:10], "big"), int.from_bytes(input_bytes[10:], "big"))

def bglDecode(input_bytes):
    output_dict = {"block":"BGL ", "size":len(input_bytes), "records":[]}
    offset = 0
    while True:
        bgl_record = bgl_record_types.get(input_bytes[offset], None)
        if bgl_record is not None:
            (bgl_record_type, bgl_record_data) = bgl_record
            output_dict["records"].append({"#id_number":0x06, "#id_name":bgl_record_type, "#memory_offset":offset, "data":[]})
            offset += 2
            for (data_id, data_type) in bgl_record_data:
                if data_type == "UINT16":
                    output_dict["records"][-1]["data"].append({"entry":data_id,"type":"UINT16","data":int.from_bytes(input_bytes[offset:offset+2], byteorder="little", signed=False)})
                    offset += 2
                elif data_type == "UINT32":
                    output_dict["records"][-1]["data"].append({"entry":data_id,"type":"UINT32","data":int.from_bytes(input_bytes[offset:offset+4], byteorder="little", signed=False)})
                    offset += 4
                elif data_type == "SINT16":
                    output_dict["records"][-1]["data"].append({"entry":data_id,"type":"SINT16","data":int.from_bytes(input_bytes[offset:offset+2], byteorder="little", signed=True)})
                    offset += 2
                elif data_type == "SINT32":
                    output_dict["records"][-1]["data"].append({"entry":data_id,"type":"SINT32","data":int.from_bytes(input_bytes[offset:offset+4], byteorder="little", signed=True)})
                    offset += 4
                elif data_type == "VAR16":
                    output_dict["records"][-1]["data"].append({"entry":data_id,"type":"VAR16","data":"0x%04x"%(int.from_bytes(input_bytes[offset:offset+2], byteorder="little", signed=False))})
                    offset += 2
                elif data_type == "VAR32":
                    output_dict["records"][-1]["data"].append({"entry":data_id,"type":"VAR32","data":"0x%08x"%(int.from_bytes(input_bytes[offset:offset+4], byteorder="little", signed=False))})
                    offset += 4
                elif data_type == "ZERO2":
                    if int.from_bytes(input_bytes[offset:offset+2], "little") != 0:
                        raise BadBlockException("%s index must be zero!"%(bgl_record_type))
                    offset += 2
        else:
            print("Unrecognized BGL record: %02x"%(input_bytes[offset]))
            break
    output_dict["remaining_data"] = input_bytes[offset:].hex(" ", -128).upper().split(" ")
    return output_dict

def parseBytes(input_bytes):
    output = []
    while len(input_bytes) > 0:    
        block_id = input_bytes[:4].decode("latin1")
        block_size = int.from_bytes(input_bytes[4:8], "little")
        if block_id == "RIFF":
            output.append({"block":"RIFF", "sub_block":parseBytes(input_bytes[8:8+block_size])})
            del input_bytes[:8+block_size]
            continue
        elif block_id == "MDL8":
            if input_bytes[4:8].decode("latin1") != "MDLH":
                raise BadBlockException("Bad MDL8 header block: must begin 'MDLH'!")
            block_size = int.from_bytes(input_bytes[8:12], "little")
            if block_size != 32:
                raise BadBlockException("Bad MDL8 header block: must be 32 bytes after the 'MDLH' and size!")
            if int.from_bytes(input_bytes[12:16], "little") != 0:
                raise BadBlockException("Bad MDL8 header block: first DWORD must be zero!")
            if int.from_bytes(input_bytes[16:20], "little") != 0:
                raise BadBlockException("Bad MDL8 header block: second DWORD must be zero!")
            model_radius = int.from_bytes(input_bytes[20:24], "little")
            if int.from_bytes(input_bytes[24:28], "little") != 0:
                raise BadBlockException("Bad MDL8 header block: fourth DWORD must be zero!")
            if int.from_bytes(input_bytes[28:32], "little") != 0:
                raise BadBlockException("Bad MDL8 header block: fifth DWORD must be zero!")
            after_offsets = int.from_bytes(input_bytes[32:36], "little")
            if input_bytes[36:40].decode("latin1") != "FS80":
                raise BadBlockException("Bad MDL8 header block: seventh DWORD must be 'FS80'!")
            if int.from_bytes(input_bytes[40:44], "little") != 2304:
                raise BadBlockException("Bad MDL8 header block: eighth DWORD must be 2304!")
            output.append({"block":"MDL8_header", "model_radius":model_radius, "after_offsets":after_offsets})
            del input_bytes[:12+block_size]
            continue
        elif block_id == "DICT":
            records = []
            for record in range(block_size//28):
                record_bytes = input_bytes[8+record*28:36+record*28]
                type_no = int.from_bytes(record_bytes[:4], "little")
                if type_no == 0:
                    if len(records) > 0:
                        if "string" not in records[-1]:
                            records[-1]["string"] = ""
                        records[-1]["string"] += record_bytes[4:].decode("latin1").rstrip("\00")
                else:
                    guid = makeGuid(record_bytes[12:])
                    data_offset = int.from_bytes(record_bytes[4:8], "little")
                    data_size = int.from_bytes(record_bytes[8:12], "little")
                    (type_name, type_size) = var_type_from_number.get(type_no, ["????", 0])
                    if (type_size != 0) and (data_size != type_size):
                        raise BadBlockException("Record found with size specified as %d bytes, but type is specified as %d which takes %d bytes!"%(data_size, type_name, type_size))
                    new_record = {"type":type_name, "offset":data_offset, "id":guid, "fs_name":fs2004_vars_dict.get(guid, {"fs_name":"<custom>"})["fs_name"]}
                    lookup_entry = fs2004_vars_dict.get(guid, None)
                    if lookup_entry is not None:
                        if lookup_entry["type"] != type_name:
                            raise BadBlockException("Record found with type specified as '%s' but variable '%s' is of type '%s'!"%(type_name, lookup_entry["fs_name"], lookup_entry["type"]))
                        new_record["fs_name"] = lookup_entry["fs_name"]
                        new_record["description"] = lookup_entry["description"]
                    records.append(new_record)
            output.append({"block":"DICT", "num_entries":len(records), "records":records})
            del input_bytes[:8+block_size]
            continue
        elif block_id == "BBOX":
            if block_size != 36:
                raise BadBlockException("Bad BBOX header block: must be 36 bytes after the size!")
            for i in range(block_size):
                if input_bytes[8+i] != 0:
                    raise BadBlockException("Bad BBOX header block: must only contain zeros after the size!")
            output.append({"block":"BBOX"})
            del input_bytes[:8+block_size]
            continue
        elif block_id == "ISFT":
            output.append({"block":"ISFT", "block_size":block_size, "creator":input_bytes[8:8+block_size].decode("latin1").rstrip("\0")})
            del input_bytes[:8+block_size]
            continue
        elif block_id == "BGL ":
            output.append(bglDecode(input_bytes[8:8+block_size]))
            del input_bytes[:8+block_size]
            continue
        raise BadBlockException("Unrecognized block type '%s'"%(block_id))
    return output
    
if __name__ == "__main__":
    for mdl_file_name in os.listdir(mdl_dir_to_parse):
        if not mdl_file_name.lower().endswith(".mdl"):
            continue
        mdl_to_parse = os.path.join(mdl_dir_to_parse, mdl_file_name)
        json_out = os.path.splitext(mdl_to_parse)[0] + ".json"
        with open(mdl_to_parse, "rb") as file_in:
            with open(json_out, "w") as file_out:
                file_out.write(json.dumps(parseBytes(bytearray(file_in.read())), indent=4, sort_keys=True))
