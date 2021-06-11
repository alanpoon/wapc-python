import threading
class ModuleState:
  
  payload = bytearray()
  guestResp = bytearray()
  guestReq = bytearray()
  guestErr = None
  hostResp = bytearray()
  hostErr = None
  hostCallHandler = None
  id = 0
  def __init__(self,hostCallHandler):
    self.lock = threading.Lock()
    self.hostCallHandler = hostCallHandler
  def getGuestRequest(self):
    with self.lock:
      return self.guestReq
  def setGuestRequest(self,payload):
    with self.lock:
      self.guestReq = payload
  def getHostResponse(self):
    with self.lock:
      return self.hostResp
  def setHostResponse(self,res):
    with self.lock:
      self.hostResp = res
  def setGuestError(self,error):
    with self.lock:
      self.guestErr =  error
  def setGuestResponse(self,res):
    with self.lock:
      self.guestResp = res
  def getGuestResponse(self):
    with self.lock:
      return self.guestResp
  def getHostError(self):
    with self.lock:
      return self.hostErr
  def setHostError(self,er):
    with self.lock:
      self.hostErr = er
  def doHostCall(self,binding,namespace,operation,payload):
    with self.lock:
      self.hostResp = None
      self.hostErr = None
      id = self.id
      if self.hostCallHandler !=None:
        result,err = self.host_callback(id,binding,namespace,operation,payload)
        if err==None:
          self.hostResp = result
          return 1
        else:
          self.hostErr = err
          return 0
      return 0
  def consoleLog(self,msg):
    print("Guest module "+self.id,":",msg)