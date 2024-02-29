# SBS streaming server by sendust

sendust streaming engine. AWS elemental encoder alternative...

ffmpeg should be located in system path

## Install

Install node and modules

```bash
npm install express node-media-server socket.io flv.js
```

Install python and modules

```bash
pip install python-socketio 
```



## Usage

Run Windows batch

```bash
1_start_server.bat
2_start_engine.bat
```


AUTO START first two encoder

```bash
python stream_2024.py 2
```


open web browser
http://localhost:5000


## Caution

Backup .json file before overwrite !!