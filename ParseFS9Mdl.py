import os
import json

mdl_dir_to_parse = "D:\\Flight\\FSX\\SimObjects\\Airplanes\\HJG Boeing KC-135A Early v6.1 BETA\\model.KC-135A_Early"

var_type_from_number = {1:["FLOAT32",4], 2:["UINT32",4], 4:["UINT16",2], 6:["FLAGS16",2], 7:["SINT16",2]}

with open("fs2004_vars.json") as f:
    fs2004_vars_dict = json.load(f)

class BadBlockException(Exception):
    pass

def hexDump(bytes_to_dump):
    output = ""
    for byte in bytes_to_dump:
        output = "%s%02x"%(output, byte)
    return output
    
def makeGuid(input_bytes):
    return "%08X-%04X-%04X-%04X-%012X"%(int.from_bytes(input_bytes[:4], "little"), int.from_bytes(input_bytes[4:6], "little"), int.from_bytes(input_bytes[6:8], "little"), int.from_bytes(input_bytes[8:10], "big"), int.from_bytes(input_bytes[10:], "big"))

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
                raise BadBlockException("MDL8 header block must begin 'MDLH'!")
            block_size = int.from_bytes(input_bytes[8:12], "little")
            output.append({"block":"MDL8_header", "raw_data":hexDump(input_bytes[12:12+block_size])})
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
                    data_size = int.from_bytes(record_bytes[8:12], "little")
                    (type_name, type_size) = var_type_from_number.get(type_no, ["????", 0])
                    if (type_size != 0) and (data_size != type_size):
                        raise BadBlockException("Record found with size specified as %d bytes, but type is specified as %d which takes %d bytes!"%(data_size, type_name, type_size))
                    new_record = {"type":type_name, "offset":int.from_bytes(record_bytes[4:8], "little"), "id":guid, "fs_name":fs2004_vars_dict.get(guid, {"fs_name":"<custom>"})["fs_name"]}
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
            output.append({"block":"BBOX", "raw_data":hexDump(input_bytes[8:8+block_size])})
            del input_bytes[:8+block_size]
            continue
        elif block_id == "ISFT":
            output.append({"block":"ISFT", "creator":input_bytes[8:8+block_size].decode("latin1").rstrip("\0")})
            del input_bytes[:8+block_size]
            continue
        elif block_id == "BGL ":
            output.append({"block":"DICT", "raw_data":"BGL DATA", "size":block_size})
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
