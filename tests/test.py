import os
import wapc
def hostCallHandler(binding, namespace, operation, payload):
  print("hostCallHandler")
  return bytearray(b'22'),None
try:
    scriptpath = os.path.dirname(os.path.realpath(__file__))
    wasm_fn = os.path.join(scriptpath, "./hello.wasm")
    f = open(wasm_fn, "rb")
    moduleState = wapc.ModuleState(hostCallHandler)
    we = wapc.WapcEngine(f.read(),moduleState)
    we.load()
    wh = wapc.WapcHost(we)
    wh.initialize()
    res = wh.call("hello",'telll'.encode())
    print("res",res.decode(encoding="UTF-8"))
except (KeyboardInterrupt, SystemExit):
    pass