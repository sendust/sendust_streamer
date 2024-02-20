
const app = require('express')();
const server = require('http').createServer(app);
const io = require('socket.io')(server);
const port = 5000;

app.get('/', function(req, res) {
   res.sendFile('index.html', {root: "./"});
});


io.on('connection', (socket) => {
  console.log('user connected  ' + socket.id);
  socket.emit('askForUserId');
  
  socket.on('disconnect', function () {
    console.log('user disconnected');
  });
  
  socket.on('msg_gui', function (data) {
    console.log('msg_gui');
	console.dir(data);
	console.log("socket id is " + socket.id);
	io.emit("msg_gui", data);
  });

	socket.on('userIdReceived', (userId) => {
	console.log("user ID Received... " + userId);
  });
	socket.on('reply_engine', (message) => {
		socket.broadcast.to(message.receiverId).emit('reply_engine', message.data);
  });
  
  
  socket.on('msg_engine', function (data) {
    console.log('msg_engine');
	console.dir(data);
	console.log("socket id is " + socket.id);
	io.emit("msg_engine", data);
  });
  

  
})


server.listen(port, function() {
  console.log(`Listening on port ${port}\nopen http://localhost:${port}`);
});