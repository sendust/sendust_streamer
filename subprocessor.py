import subprocess, shlex, threading, time, os, ctypes

#  subprocess launcher by sendust
#  specialized for ffmpeg
#
#  2024/1/26
#  2024/2/7    Add some function, properties..(set_finishfile, self.str_run ...)
#  2024/2/14   Add watch dog, pid_running


def pid_running(pid):         # for windows version
    kernel32 = ctypes.windll.kernel32
    SYNCHRONIZE = 0x100000
    process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
    if process != 0:
        kernel32.CloseHandle(process)
        return True
    else:
        return False

class launcher:
    def __init__(self):
        self.str_run = ''
        self.name_thread = ''
        self.timeout = 43200 # 12 hours
        self.out_position = 0
        self.out_progress = 'undetermined..'
        self.duration = 0
        self.file_finish = ''
        self.str_run = 'This is example..'
        self.fn_info = print
        self.enable_watchdog = False
        self.wtimer = ''
        self.updatelog = print
        self.osenv = {}     # dict type.. {"FFREPORT" : f'file=FFMPEG_MXF_{self.nameonly}.LOG:level=32'}
        self.workdir = os.path.join(os.getcwd(), "debug")
    
    def set_name(self, name):
        self.name_thread = name
    
    def set_finishfile(self, f):
        self.file_finish = f
    
    def set_timeout(self, time):
        self.timeout = time
    
    def set_duration(self, time):
        self.duration = time
    
    def set_fn_report(self, info_fn):
        self.fn_info = info_fn

    def set_fn_updatelog(self, updatelog_fn):
        self.updatelog = updatelog_fn

    def set_watchdog(self, onoff):
        self.enable_watchdog = onoff
    
    def set_osenv(self, dict):
        self.osenv = dict
    
    def watchdog(self):
        self.updatelog((f'[{self.name_thread}] Watch dog pid is {self.process.pid}/{self.watchdog_now}'))
        if self.watchdog_last == self.watchdog_now:
            self.updatelog(f'[{self.name_thread}] No response from process.. kill')
            p = subprocess.run(f'taskkill /f /pid {self.process.pid}', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.updatelog(f'[{self.name_thread}] taskkill return code {p.returncode}')
            self.finish()
            return
        self.watchdog_last = self.watchdog_now
        if pid_running(self.process.pid):
            self.wtimer = threading.Timer(3, self.watchdog)
            self.wtimer.name =  f'{self.name_thread}_{self.process.pid}'
            self.wtimer.start()
            
    def run(self, str_run):
        self.tm_start = time.time()
        self.out_position = 0
        self.str_run = str_run
        self.process = subprocess.Popen(shlex.split(str_run), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8", errors="replace", universal_newlines=True)
        self.thread = threading.Thread(target=self.get_pipe, name=self.name_thread)
        self.thread.start()
        if self.enable_watchdog:
            self.watchdog_last = "------------"
            self.watchdog_now = "-----------X"
            self.wtimer = threading.Timer(5, self.watchdog)
            self.wtimer.name = f'{self.name_thread}_{self.process.pid}'
            self.wtimer.start()
    
    def runwait(self, str_run):
        self.tm_start = time.time()
        self.out_position = 0
        # Setup os env variable
        if not self.osenv:
            self.osenv = {"FFREPORT" : f'file=FFMPEG_debug_{time.strftime("%Y%m%d-%H%M%S")}.LOG:level=32'}
        newenv = os.environ.copy()
        for key in self.osenv:
            newenv[key] = self.osenv[key]
        # Open process
        self.str_run = str_run
        self.process = subprocess.Popen(shlex.split(str_run), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8", errors="replace", universal_newlines=True, env=newenv, cwd=self.workdir)
        if self.enable_watchdog:
            self.watchdog_last = "------------"
            self.watchdog_now = "-----------X"
            self.wtimer = threading.Timer(5, self.watchdog)
            self.wtimer.name = f'{self.name_thread}_{self.process.pid}'
            self.wtimer.start()
        self.get_pipe()
    
    def hmstosecond(self, str):
        hms = str.split(":")
        t = int(hms[0]) * 3600 + int(hms[1]) * 60 + float(hms[2])
        return t
    
    def decode_ffmpegoutput(self, line):
        line_ = line.strip().split(" ")
        self.watchdog_now = line.strip()
        #print(f'compare watchdog\n{self.watchdog_now} <->{self.watchdog_last}')
        for each in line_:

            if each.startswith("time="):
                parseline = each.split("=")
                t = self.hmstosecond(parseline[1])
                self.out_position = t
                #self.out_progress = f'{parseline[1]}  [{self.out_position}/{self.duration}]'
                self.out_progress = f'{parseline[1]}'
                self.fn_info({self.name_thread : self.out_progress})
                #print(self.out_progress)

        
    def get_pipe(self):
        while ((time.time() - self.tm_start) < self.timeout):
# Check if child process has terminated. Set and return returncode attribute. Otherwise, returns None.
            output = self.process.stdout.readline()   
            if output == '' and self.process.poll() is not None:
                break
            if output:
                try:
                    if output.startswith("frame="):
                        self.decode_ffmpegoutput(output)
                    else:
                        print(output.strip())
                        x = output.find("Duration: ")
                        if ((x > -1) and (not self.duration)):
                            self.updatelog(f'[{self.name_thread}] ## Duration detected....  {output[x+10:x+21]}')
                            self.duration = self.hmstosecond(output[x+10:x+21])
                except Exception as e:
                    print(e)
        
        # There is no stdout and process finished       
        self.finish()

    def finish(self):
        try:
            self.process.terminate()
            if self.wtimer:
                self.wtimer.cancel()
        except Exception as e:
            print(e)

        try:
            return_code = self.process.poll()
            if return_code != 0:
                self.updatelog(f'[{self.name_thread}] ffmpeg process exited with error code {return_code}')
            else:
                self.updatelog(f'[{self.name_thread}] ffmpeg process completed successfully')

        except Exception as e:
            print(e)

        if self.file_finish:
            with open(self.file_finish, 'w', encoding='utf-8') as f:
                f.writelines(self.str_run)

def get_stdout(str_run):
    p = subprocess.run(shlex.split(str_run), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8", errors="replace", universal_newlines=True)
    return p.stdout


if __name__ == "__main__":
    encoder = launcher()
    encoder.set_name("testsig")
    #encoder.set_timeout(10)
    encoder.runwait("ffmpeg -f lavfi -re -i testsrc -c:v mpeg2video -f null -")