import os
import json

mdl_dir_to_parse = "D:\\Flight\\FSX\\SimObjects\\Airplanes\\HJG Boeing KC-135A Early v6.1 BETA\\model.KC-135A_Early"

class BadBlockException(Exception):
    pass

def hexDump(bytes_to_dump):
    output = ""
    for byte in bytes_to_dump:
        output = "%s%02x"%(output, byte)
    return output

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
                records.append({"type":int.from_bytes(record_bytes[:4], "little"), "offset":int.from_bytes(record_bytes[4:8], "little"),"spacing":int.from_bytes(record_bytes[8:12], "little"), "id":hexDump(record_bytes[12:])})
            output.append({"block":"DICT", "records":records})
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
