const http = require('http');
const express = require('express');
const socketIO = require('socket.io');
//const cors = require('cors')
const PORT = 5000;

const app = express();
const server = http.createServer(app);
const io = socketIO(server, {maxHttpBufferSize: 1e8});

const NodeMediaServer = require('node-media-server');

const config = {
  rtmp: {
    port: 8935,
    chunk_size: 60000,
    gop_cache: true,
    ping: 30,
    ping_timeout: 60
  },
  http: {
    port: 8936,
    allow_origin: '*'
  }
};


//app.use(cors())
var nms = new NodeMediaServer(config)
nms.run()


app.get('/', function(req, res) {
   res.sendFile('index.html', {root: "./"});
});


app.get('/flv.min.js', function(req, res) {
   res.sendFile('/flv.js/dist/flv.min.js', {root: "./node_modules"});
});

app.get('/favicon.ico', function(req, res) {
   res.sendFile('/favicon.ico', {root: "./"});
});



io.on('connection', (socket) => {
    console.log('A user connected' + socket.id);

    socket.on('disconnect', () => {
        console.log('User disconnected' + socket.id);
    });

    // Listen for messages from a client
    socket.on('message', (message) => {
        console.log(`Received msg  ${socket.id}  : ${Object.keys(message)}`);
        
        // Broadcast the received message to all connected clients
        socket.broadcast.emit('message', message);
    });
});

server.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
