prefix = "~/Documents/attendance" //The following code works for my file structure; If you change your file structure change this line and prepend this prefix to every relevant data value
function getData(){
	dic = {
		'inp_vid': document.getElementById('inp_vid').value,
		'imdir': document.getElementById('imdir').value,
		'data': document.getElementById('data').value,
		'dtime': document.getElementById('dtime').value,
		'inp_mod': document.getElementById('inp_mod').value,
		'con_vid': document.getElementById('con_vid').value,
		'fps': document.getElementById('fps').value,
		'loc': document.getElementById('loc').value,
		'sav_box': document.getElementById('sav_box').value,
		'lo_box': document.getElementById('lo_box').value,
		'ove_vid': document.getElementById('con_vid').value,
		'out_vid': document.getElementById('inp_vid').value
	}
	dic["ove_vid"] = dic["ove_vid"].substring(0,dic["ove_vid"].length - 4) + ".avi"
	dic["out_vid"] = dic["out_vid"].substring(0,dic["out_vid"].length - 4) + "_out.mp4"
	return dic	
}
function setVideo(vid,sid,link){
	var video = document.getElementById(vid);
	var source = document.getElementById(sid);
	video.pause();
	source.setAttribute('src', link); 
	video.load();
	video.play();
}
function fixPath(data){
	data["inp_vid"] = data["inp_vid"].substring(1)//prefix + data["inp_vid"]
	data["con_vid"] = data["con_vid"].substring(1)//prefix + data["con_vod"]
	data["ove_vid"] = data["ove_vid"].substring(1)//prefix + data["ove_vid"]
	data["out_vid"] = data["out_vid"].substring(1)//prefix + data["out_vid"]
	return data
}
function test(){
	console.log("Testing With Data")
	console.log(getData())
	inpData = getData()
	setVideo("read_vid", "read_vid_src", inpData['inp_vid'])
	setVideo("write_vid", "write_vid_src", document.getElementById("write_vid_src").src)
	conVid = inpData["con_vid"]
	$.get({
		url: '/run/test',
		data: fixPath(inpData),
		success: function(data){
			console.log(data)
			setVideo("write_vid", "write_vid_src", conVid)
		},
		error: function(data){
			console.log(data)
		}
	});
}
function train(){
	console.log("Training With Data")
	console.log(getData())	
	setVideo("read_vid", "read_vid_src", getData()['inp_vid'])
	setVideo("write_vid", "write_vid_src", document.getElementById("write_vid_src").src)
	$.get({
		url: '/run/train',
		data: fixPath(getData()),
		success: function(data){
			console.log(data)
		},
		error: function(data){
			console.log(data)
		}
	});
}
setVideo("read_vid","read_vid_src","https://user.tjhsst.edu/2019ssaxena/landing/css/this_is_america.mp4")
