#!/usr/bin/env python3

import os, sys, struct, time, io
import wasm3


RegisterFunc =[]
def wasi_generic_api(func):
    for modname in ["wasi_unstable", "wasi_snapshot_preview1"]:
        def wrapper(*args):
          return func(*args)
        RegisterFunc.append({"mode_name":modname,"func_name":func.__name__,"func":wrapper})
    return func

def wapc_generic_api(func):
    for modname in ["wapc"]:
        def wrapper(*args):
          return func(*args)
        RegisterFunc.append({"mode_name":modname,"func_name":func.__name__,"func":wrapper})
    return func
global moduleStateGlobal
global rtGlobal
operationGlobal =""
class WapcEngine:
  mod = None
  rt = None
  moduleState = None
  msg = ""
  def __init__(self, wasmBytes,moduleState,size=32*1024):
    env = wasm3.Environment()
    self.rt = env.new_runtime(size)
    self.mod = env.parse_module(wasmBytes)
    self.moduleState = moduleState
  def load(self):
    self.rt.load(self.mod)
    for r in RegisterFunc:
      self.mod.link_function(r["mode_name"],r["func_name"],r["func"])
    global rtGlobal
    global moduleStateGlobal
    rtGlobal = self.rt
    moduleStateGlobal = self.moduleState
  @wasi_generic_api
  def args_sizes_get(argc, buf_sz):
    mem = rtGlobal.get_memory(0)
    struct.pack_into("<I", mem, argc,   2)
    struct.pack_into("<I", mem, buf_sz, 32)
    return WasiErrno.SUCCESS
  @wasi_generic_api
  def args_get(argv, buf):
      mem = rtGlobal.get_memory(0)
      struct.pack_into("<II", mem, argv, buf, buf+8)
      struct.pack_into("8s4s", mem, buf, b"WASM\0")
      return WasiErrno.SUCCESS

  @wasi_generic_api
  def fd_write(fd, iovs, iovs_len, nwritten):
    mem = rtGlobal.get_memory(0)
    # get data
    data = b''
    for i in range(iovs_len):
        iov = iovs+8*i
        (off, size) = struct.unpack("<II", mem[iov:iov+8])
        data += mem[off:off+size].tobytes()
    if fd == 1 or fd == 2:     # stdout, stderr
        print(data.decode(), end='')
    else:
        print(f"Cannot write fd: {fd}")
        return WasiErrno.BADF
    return WasiErrno.SUCCESS
  @wapc_generic_api
  def __guest_request(operationPtr,payloadPtr):
    mem = rtGlobal.get_memory(0)
    encoded_string = operationGlobal.encode()
    byte_array = bytearray(encoded_string)
    mem[operationPtr:operationPtr+len(byte_array)] = byte_array
    guestReq = moduleStateGlobal.getGuestRequest()
    mem[payloadPtr:payloadPtr+len(guestReq)] = guestReq
  @wapc_generic_api
  def __guest_response(ptr,length):
    mem = rtGlobal.get_memory(0)
    buf = bytearray(length)
    buf[:] = mem[ptr:ptr+length]
    moduleStateGlobal.setGuestResponse(buf)

  @wapc_generic_api
  def __guest_error(ptr,length):
    mem = rtGlobal.get_memory(0)
    buf = bytearray(length)
    buf[:] = mem[ptr:ptr+length]
    moduleStateGlobal.setGuestError(buf.decode())
  @wapc_generic_api
  def __host_call(bindingPtr,bindingLen,namespacePtr,namespaceLen, operationPtr, operationLen, payloadPtr, payloadLen):
    if moduleStateGlobal.hostCallHandler ==None:
      return 0
    mem = rtGlobal.get_memory(0)
    binding = bytes(mem[bindingPtr:bindingPtr+bindingLen]).decode()
    namespace = bytes(mem[namespacePtr:namespacePtr+namespaceLen]).decode()
    operation = bytes(mem[operationPtr:operationPtr+operationLen]).decode()
    payload = bytearray(payloadLen)
    payload[:] = mem[payloadPtr:payloadPtr+payloadLen]
    hostResp, hostErr = moduleStateGlobal.hostCallHandler(binding,namespace,operation,payload)
    moduleStateGlobal.setHostResponse(hostResp)
    moduleStateGlobal.setHostError(hostErr)
    if hostErr!= None:
      return 0
    return 1
  @wapc_generic_api
  def __host_response_len():
    hostResp = moduleStateGlobal.getHostResponse()
    return len(hostResp)

  @wapc_generic_api
  def __host_response(ptr):
    mem = rtGlobal.get_memory(0)
    hostResp = moduleStateGlobal.getHostResponse()
    mem[ptr:ptr+len(hostResp)]= moduleStateGlobal.getHostResponse()
    
  @wapc_generic_api
  def __host_error_len(self):
    hostErr = moduleStateGlobal.getHostError()
    if hostErr != None:
      return len(hostErr)
    else:
      return 0
  @wapc_generic_api
  def __host_error(self,ptr):
    mem = rtGlobal.get_memory(0)
    hostErr = moduleStateGlobal.getHostError()
    if hostErr != None:
      mem[ptr:] = bytearray(hostErr,encoding="UTF-8")

  @wapc_generic_api
  def __console_log(self,str,len):
    mem = rtGlobal.get_memory(0)
    self.msg = mem[str : str+len].decode()
class Invocation:
  op = ""
  msg = bytearray()
  def __init__(self,op,msg):
    self.op = op
    self.msg = msg
  def len(self):
    return len(bytearray(self.op,encoding="UTF-8")),len(self.msg)

class WapcHost:
  wasmEngine = None
  def __init__(self,wasmEngine):
    self.wasmEngine = wasmEngine
  def initialize(self):
    wasm_start = self.wasmEngine.rt.find_function("_start")
    wasm_start()
  def id(self):
    pass
  def call(self,op,payload):
    global operationGlobal
    operationGlobal = op
    invocation = Invocation(op,payload)
    moduleStateGlobal.setGuestRequest(payload)
    guest_call = self.wasmEngine.rt.find_function("__guest_call")
    operation_size,payload_size = invocation.len()
    res = guest_call(operation_size,payload_size)
    if res==1:
      return moduleStateGlobal.getGuestResponse()      
    else:
      return bytearray()

class WasiErrno:
    SUCCESS = 0
    BADF    = 8
    INVAL   = 28
