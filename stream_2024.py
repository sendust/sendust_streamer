#  AWS elemental encoder alternative.
#  Code managed by sendust, SBS (2024~)
#  node, express, ffmpeg
#   2024/2/17   first code.
#   2024/2/21   Improve encoder thread handling, logging, more protocol commands
#   2024/3/18   ffreport message tolerance 300 -> 3000




import time, threading, socketio, sys, datetime, os, json
from queue import Queue

import subprocessor
from splitpath import get_filesize
from sendustlogger import updatelog

class sioclient():
    def __init__(self):
        print('Create python socket.io object')
        self.sio = socketio.Client(reconnection = True, reconnection_delay=0.1, request_timeout = 0.1)
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("message", self.on_msg_gui)
        self.recv_fn = print
        
    def on_connect(self):
        print('connection established', self.sio.sid)
    
    def set_recv_fn(self, fn):
        self.recv_fn = fn
    
    def on_msg_gui(self, data):
        print('message received =>', data)
        self.recv_fn(data)

    def on_disconnect(self):
        print('disconnected from server')
        
    def connect(self, address):
        self.address = address

        result = False
        try:
            self.sio.connect(address)
            result = True
        except Exception as e:
            print(e)
            result = False
        finally:
            return result

    def disconnect(self):
        try:
            self.sio.disconnect()
        except Exception as e:
            print(e)

    def send_2(self, name_event, data):
        try:
            self.sio.emit(name_event, data)
        except Exception as e:
            print(e)
            

    def send(self, name_event, data):
        if self.sio.connected:
            self.sio.emit(name_event, data)
        else:
            self.disconnect()
            self.connect(self.address)
        


class webgui:

    def start(self, recv_fn):
        updatelog("Start web GUI..")
        self.sio = sioclient()
        self.sio.set_recv_fn(recv_fn)
        if (not self.sio.connect('http://localhost:5000')):
            updatelog("Cannot establish socketio... check server..")
            return

    def send(self, msg):
        try:
            self.sio.send('message', msg)
        except Exception as e:
            print(e)

class encoder:
    def __init__(self, name):
        self.name = name
        self.keep_running = True
        self.isrunning = False
        self.size_ffreport_before = 15000
        self.json_param_f = name + 'param.json'
        self.param = {}

    def start(self):
        if self.isrunning:
            updatelog(f'[{self.name}]Already running. reason : FLAG isrunning !')
            send_eneginemsg(f'[{self.name}]Already running. reason : FLAG isrunning !')
            return
        if self.name in get_all_threadname():
            updatelog(f'[{self.name}]Already running. reason : threadname')
            send_eneginemsg(f'[{self.name}]Already running. reason : threadname')
            return
        self.thread = threading.Thread(target=self.run, name=f'{self.name}_enc')
        self.thread.start()
        
    def run(self):
        self.keep_running = True
        while self.keep_running:
            self.isrunning = True
            self.enc = subprocessor.launcher()
            self.ffreport = os.path.join(os.getcwd(), 'debug' , f'FFMPEG_debug_{self.name}.LOG')
            self.enc.set_osenv({"FFREPORT" : f'file=FFMPEG_debug_{self.name}.LOG:level=24'})
            self.enc.set_name(self.name + "stat")
            self.enc.set_fn_report(sio_encoder_report)
            self.enc.set_watchdog(True)
            self.enc.set_fn_updatelog(updatelog)
            self.timer_cancel()
            self.timer(self.watchdog, 2)
            t_start = time.time()
            run_str = self.decode_param(self.param.get("param"))
            self.size_ffreport_before = 15000
            updatelog(f'[{self.name} run with param] ==> \n{run_str}')
            try:
                self.enc.runwait(run_str)
            except Exception as e:
                updatelog(f'[{self.name} Encoder startup fail \n{e}')
            if ((time.time() - t_start) < 2):   # ffmpeg startup fail
                #self.keep_running = False
                self.timer_cancel()
                self.score_fail = 0
                updatelog(f'[{self.name}]Encoder exited immediately. Reason ->\n{self.read_ffreport()}')
                updatelog(f'[{self.name}]Wait until next retry...')
                while (self.keep_running and (time.time() - t_start < 15)):
                    time.sleep(0.1)
            self.isrunning = False
            updatelog(f'[{self.name} Finish encoder')
        self.isrunning = False
        updatelog(f'[{self.name}] Finish encoder. escape from running loop')

    def read_ffreport(self):
        try:
            with open(self.ffreport, "r") as f:
                result = f.read()
        except Exception as e:
            print(e)
            result = ''
        return result
    
    def set_run_param(self, param):
        self.run_param = self.decode_param(param)
    
    def timer(self, fn, period):
        self.T = threading.Timer(period, fn)
        self.T.name = f'{self.name}_TMR'
        self.T.start()
    
    def timer_cancel(self):
        try:
            self.T.cancel()
        except Exception as e:
            print(e)
    
    def stop(self):
        updatelog(f'[{self.name}]Stop encoder..')
        try:
            self.keep_running = False
            self.timer_cancel()
            self.isrunning = False
            self.enc.process.kill()
        except Exception as e:
            updatelog(f'[{self.name}]Error while stop encoder.. \n{e}')


    def kill(self):
        updatelog(f'[{self.name}]Kill encoder..')
        try:
            self.enc.process.kill()
        except Exception as e:
            updatelog(f'[{self.name}] Error while kill process..\n{e}')
            

    def watchdog(self):
        # print('ffreport file size is ' , get_filesize(self.ffreport))
        size_ffreport = get_filesize(self.ffreport)
        sio_encoder_report({f'{self.name}ffreport' : size_ffreport})
        size_delta_ffreport = size_ffreport - self.size_ffreport_before
        if size_delta_ffreport:
            updatelog(f'[{self.name}]ffreport size changed - \n{self.read_ffreport()}')
        if size_delta_ffreport > 3000:   # tee, DTS error message > 800  (very long)
            updatelog(f'[{self.name}]ffreport delta has abnormal size.. kill encoder')
            self.kill()
            time.sleep(0.1)
        if subprocessor.pid_running(self.enc.process.pid):
            self.timer(self.watchdog, 1)
        self.size_ffreport_before = size_ffreport

        tm_reset = self.param.get("timetb").split("\n")
        tm_reset = [each.strip() + ".00" for each in tm_reset] # HH:MM.00 
        now = time.strftime("%H:%M.%S")
        if now in tm_reset:
            updatelog(f'[{self.name}]killed, reason=reset time {tm_reset}')
            self.kill()
            
# consider tee long message...
#[aac @ 0000026cb95b4e40] Queue input is backward in time
#[tee @ 0000026cb956fc40] Non-monotonous DTS in output stream 0:1; previous: 143363, current: 141678; changing to 143364. This may result in incorrect timestamps in the output file.
#[tee @ 0000026cb956fc40] Non-monotonous DTS in output stream 0:1; previous: 143364, current: 142702; changing to 143365. This may result in incorrect timestamps in the output file.
#[aac @ 0000026cc6b0b640] Queue input is backward in time
#[tee @ 0000026cb956fc40] Non-monotonous DTS in output stream 0:2; previous: 143363, current: 141678; changing to 143364. This may result in incorrect timestamps in the output file.
#[tee @ 0000026cb956fc40] Non-monotonous DTS in output stream 0:2; previous: 143364, current: 142702; changing to 143365. This may result in incorrect timestamps in the output file.


    def load_param(self):
        with open(self.json_param_f, "r") as f:
            self.param = json.load(f)
            self.set_run_param(self.decode_param(self.param.get("param")))
        return self.param
        
    def save_param(self, data_save):
        with open(self.json_param_f, "w") as f:
            jdump = json.dumps(data_save)
            f.write(jdump)
            self.set_run_param(data_save.get("param"))
        return jdump

    def decode_param(self, param):
        first_valid = ''
        for each in param.split('\n'):
            if each.strip().startswith("ffmpeg"):
                first_valid = each.strip()
                break
        return first_valid



class preset:
    # This is dummy preset.. actual preset is loaded from json file..
    dict_preset = {"preset1" : "1", "preset2" : "2",
            "preset3" : "3" , "preset4" : "4",
            "preset5" : "5", "preset6" : "6",
            "preset7" : "7", "preset8" : "8",
            "preset9" : "9", "preset10" : "10"}
    
    dict_protocol_get = {"preset1get" : "preset1", "preset2get" : "preset2",
            "preset3get" : "preset3", "preset4get" : "preset4",
            "preset5get" : "preset5", "preset6get" : "preset6",
            "preset7get" : "preset7", "preset8get" : "preset8",
            "preset9get" : "preset9", "preset10get" : "preset10"}
    
    dict_protocol_set = {"preset1set" : "preset1", "preset2set" : "preset2",
            "preset3set" : "preset3", "preset4set" : "preset4",
            "preset5set" : "preset5", "preset6set" : "preset6",
            "preset7set" : "preset7", "preset8set" : "preset8",
            "preset9set" : "preset9", "preset10set" : "preset10"}
    
    def write(self):
        try:
            with open("preset.json", "w") as f:
                f.write(json.dumps(self.dict_preset))
        except Exception as e:
            print(e)

    def read(self):
        try:
            with open("preset.json", "r") as f:
                self.dict_preset = json.load(f)
        except Exception as e:
            print(e)
        updatelog(f'Read preset from file...\n{self.dict_preset}')


    def get_preset(self, protocol):
        print(f'protocol is {protocol}')
        print(f'decoded preset is {self.dict_protocol_get.get(protocol)}')
        param = self.dict_preset.get(self.dict_protocol_get.get(protocol))
        updatelog(f'get preset\n{param}')
        return param
    
    
    def set_preset(self, protocol, data):
        self.dict_preset[self.dict_protocol_set[protocol]] = data
        self.write()
        

def decode_protocol(protocol):
    global pst, enc1, enc2, enc3, enc4, enc5, enc6, keep_run
    updatelog(f'decode protcol ->  {protocol}')
    try:
        cmd = protocol.get("cmd")
    except:
        cmd = "unknown"
    
    if cmd.startswith("shell"):
        cmd_shell = cmd[5:].strip()
        res = subprocessor.get_stdout(cmd_shell, "cp949")
        wg.send({"enginemsg" : res})
        return
        
    
    if cmd in ["halt", "shutdown"]:
        keep_run = False
        for each in [enc1, enc2, enc3, enc4, enc5, enc6]:
            each.stop()
        sys.exit(1)
    
    if cmd in ["startall", "allstart"]:
        for each in [enc1, enc2, enc3, enc4, enc5, enc6]:
            updatelog(f'{each.name} start encoder from command..')
            each.start()
        return
        
    if cmd in ["stopall", "allstop"]:
        for each in [enc1, enc2, enc3, enc4, enc5, enc6]:
            each.stop()
        return

    if cmd in ["killall", "allkill"]:
        for each in [enc1, enc2, enc3, enc4, enc5, enc6]:
            each.kill()
        return


    if cmd in pst.dict_protocol_get:    # preset ENGINE -> GUI
        updatelog("do preset get cmd")
        param = pst.get_preset(cmd)
        updatelog(param)
        #wg.send({"id_param" : param})
        #wg.send({"enginemsg" : f'read {cmd} parameter..'})
        wg.send({"enginemsg" : param})
        return
        
    if cmd in pst.dict_protocol_set:       # preset GUI -> ENGINE
        updatelog("do preset set cmd")
        param = protocol["data"]["param"]
        updatelog(param)
        pst.set_preset(cmd, param)
        #wg.send({"enginemsg" : f'write {cmd} parameter..'})
        return
    
    dict_cmd_start = {"enc1start" : enc1.start, "enc2start" : enc2.start,
                    "enc3start" : enc3.start, "enc4start" : enc4.start,
                    "enc5start" : enc5.start, "enc6start" : enc6.start}
                    
    dict_cmd_stop = {"enc1stop" : enc1.stop, "enc2stop" : enc2.stop,
                    "enc3stop" : enc3.stop, "enc4stop" : enc4.stop,
                    "enc5stop" : enc5.stop, "enc6stop" : enc6.stop}
                    
    dict_cmd_get = {"enc1get" : enc1, "enc2get" : enc2,
                    "enc3get" : enc3, "enc4get" : enc4,
                    "enc5get" : enc5, "enc6get" : enc6}
                    
    dict_cmd_set = {"enc1set" : enc1, "enc2set" : enc2,
                    "enc3set" : enc3, "enc4set" : enc4,
                    "enc5set" : enc5, "enc6set" : enc6 }               

    dict_cmd_get_title = {"enc1get" : "enc1title", "enc2get" : "enc2title",
                        "enc3get" : "enc3title", "enc4get" : "enc4title",
                        "enc5get" : "enc5title", "enc6get" : "enc6title"}

    if cmd in dict_cmd_start:
        fn = dict_cmd_start.get(cmd)
        fn()
        return

    if cmd in dict_cmd_stop:
        fn = dict_cmd_stop.get(cmd)
        fn()
        return

    if cmd in dict_cmd_get:
        enc = dict_cmd_get.get(cmd)
        enc.load_param()
        wg.send({"id_param" : enc.param.get("param")})
        wg.send({"id_timetable" : enc.param.get("timetb")})
        wg.send({dict_cmd_get_title.get(cmd) : enc.param.get("title")})
        wg.send({"enginemsg" : enc.read_ffreport()})
        return

    if cmd in dict_cmd_set:
        enc = dict_cmd_set.get(cmd)
        data_save = protocol.get("data")
        enc.save_param(data_save)
        enc.load_param()
            
    if cmd == "getdshow":
        updatelog("show dshow devices..")
        s = subprocessor.get_stdout(f'ffmpeg -hide_banner -f dshow -list_devices 1 -i dummy -f null -')
        updatelog(s)
        wg.send({"enginemsg" : s})
                
    if cmd == "getdecklink":
        updatelog("show decklink devices..")
        s = subprocessor.get_stdout(f'ffmpeg -hide_banner -f decklink -list_devices 1 -i dummy -f null -')
        updatelog(s)
        wg.send({"enginemsg" : s})
        

def sio_encoder_report(data):
    global wg
    wg.send(data)

def send_eneginemsg(data):
    global wg
    wg.send({"enginemsg" : data})


def get_all_threadname():
    tlist = [t.name for t in threading.enumerate()]
    return tlist
    
    
wg = webgui()
wg.start(decode_protocol)

enc1 = encoder("enc1")
enc2 = encoder("enc2")
enc3 = encoder("enc3")
enc4 = encoder("enc4")
enc5 = encoder("enc5")
enc6 = encoder("enc6")
list_encoder = [enc1, enc2, enc3, enc4, enc5, enc6]


wg.send({"enginemsg" : "Encoder Created...\nApplication Started...."})
pst = preset()
pst.read()

for each in list_encoder:
    updatelog(each.load_param())

try:
    autostart = int(sys.argv[1])
except:
    autostart = 0
    updatelog(f'Encoder auto start disabled....')
    
for i in range(autostart):      # auto start encoder 
    updatelog(f'Auto start encoder .... {i}')
    list_encoder[i].start()



keep_run = True

try:
    while keep_run:
        print(time.time(), get_all_threadname(),  end="\r")
        wg.send({"now" : time.strftime("%Y/%m/%d-%H:%M.%S")})
        time.sleep(1)
except KeyboardInterrupt:
    keep_run = False
    for each in list_encoder:
        each.stop()
        