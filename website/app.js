#!/usr/bin/nodejs

// -------------- load packages -------------- //
var express = require('express');
var app = express();
var path = require('path');
var hbs = require( 'express-handlebars' )//require('hbs');
var cookieSession = require('cookie-session')
var simpleoauth2 = require("simple-oauth2");
var request = require('request');
const fs = require('fs')
var mysql = require('mysql');
var server =  require('http').createServer(app);
var io = require('socket.io').listen(server); 
var os = require('os')
const { spawn } = require('child_process');
server.listen(process.env.PORT || 8080); 
// -------------- express initialization -------------- //
app.set('port', process.env.PORT || 8080 );
app.engine( 'hbs', hbs( { 
  extname: 'hbs', 
  partialsDir: __dirname + '/views/partials/'
} ) );
app.set('view engine', 'hbs');

//cookies//
app.set('trust proxy', 1) // trust first proxy 

app.use(cookieSession({
  name: 'snorkles',
  keys: ['HelloSecretKey', 'ThisIsRoot']
}))


// -------------- serve static folders -------------- //
app.use('/home/js', express.static(path.join(__dirname, 'js')))
app.use('/home/css', express.static(path.join(__dirname, 'css')))
app.use('/run/js', express.static(path.join(__dirname, 'Run', 'js')))
app.use('/css/css', express.static(path.join(__dirname, 'Run', 'css')))
app.use('/videos', express.static(path.join(__dirname, '..', 'Videos')))
// -------------- variable definition -------------- //
var visitorCount = 0; 
// -------------- express 'get' handlers -------------- //
app.get('/', function(req,res){
	res.redirect('127.0.0.1:8080/home')
});
app.get('/info', function(req, res){
    res.redirect('https://user.tjhsst.edu/2019ssaxena/attendance')//.render(path.join(__dirname,'index.hbs'),{'profile':req.session.profile});
});
app.get('/home', function(req, res){
    res.render(path.join(__dirname,'index.hbs'),{'profile':req.session.profile});
});
app.get('/run', function(req,res){
	res.render(path.join(__dirname,'Run','index.hbs'),{'title': 'Classroom Attendance Bot'});
});
app.get('/run/test', function(req,res){
	q = req.query
	console.log("TEST: Creating Child Process")
	const child = spawn('bash', ['../read_and_classify_web.sh', q['inp_vid'], q['sav_box'], q['out_vid'], q['ove_vid'], q['con_vid'], q['imdir'], q['data'], q['loc'], q['fps'], q['dtime'], q['inp_mod']]);
	//child.stdout.setEncoding('utf8');
	child.stdout.on('data', (chunk) => {
		console.log("TEST: " + chunk);
	});
	child.on('close', (code) => {
		console.log('TEST: child process exited');
	});
	res.send(req.query);
});
app.get('/run/train', function(req,res){
	res.send(req.query);
});
app.get('/:page',function(req,res){
    res.render(path.join(__dirname,'err.hbs'),{})
});
