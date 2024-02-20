import os, datetime


def updatelog(txt, consoleout = True):
    pid = os.getpid()
    path_log = os.path.join(os.getcwd(), 'log', f'history_[{pid}].log')
    tm_stamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f   ")
    
    try:
        if (os.stat(path_log).st_size > 3000000):
            path_archive = os.path.splitext(path_log)[0]
            path_archive += '_' + datetime.datetime.now().strftime("_%m%d%Y-%H%M%S.log")
            os.rename(path_log, path_archive)
    except:
        print("Log with file....")
        
    txt = str(txt)
    with open(path_log, "a", encoding='UTF-8') as f:
        f.write(tm_stamp + txt + "\n")
    if consoleout:
        col = os.get_terminal_size().columns
        print(" " * (int(col) - 1), end='\r')     # clear single line
        print(tm_stamp + txt)