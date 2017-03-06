
from sheethandler import sheethandler
import traceback

def recognizeJPG(path, sheet_type):
    '''
    given path and type, return the recognition result in dictionary format:
    Success
        {"status": "success", "path": "/path/to/file", "result": {"id": ..., }}
    Failure:
        {"status": "error", "path": "/path/to/file", "message": "error messages..."}
    '''
    try:
        result = sheethandler.recognizeSheet(path, sheet_type)
        return {"status": 'success', "path": path, "result": result}
    except:
        message = traceback.format_exc()
        return {"status": 'error', "path": path, "message": message}
