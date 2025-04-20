
import xmltodict
import gzip

global plugin_ids
plugin_ids = []

#TENABLE_RANGES = list((10001, 98000), (99000, 112290), (117291, 500000))
TENABLE_RANGES = list(range(10001, 98000)) + list(range(99000, 112290)) + list(range(117291, 500000))

def _extract_script_id(_, nasl):
    """
    Takes a NASL xml block and extracts the script_id value to append to self.plugin_ids.
    """
    # If not dict then skip (should never occur)
    if type(nasl) is not dict:
        return True
    
    script_id = int(nasl["script_id"])
    # Skip plugins from the Tenable.OT platform (plugins >= 500k) as they all 404
    if script_id in TENABLE_RANGES:
    #if (10001 <= script_id < 98000) or (99000 <= script_id < 112290) or (117291 <= script_id < 500000):
        plugin_ids.append(nasl["script_id"])
    # else:
    #     print(nasl["script_id"])
    return True

#print(TENABLE_RANGES)
xmltodict.parse(gzip.GzipFile("plugin_rba_113725_Mar031741725421.xml.gz"), item_depth=2, item_callback=_extract_script_id)
print(len(plugin_ids))