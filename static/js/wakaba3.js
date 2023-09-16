function get_cookie(name) {
	with(document.cookie) {
		var regexp=new RegExp("(^|;\\s+)"+name+"=(.*?)(;|$)");
		var hit=regexp.exec(document.cookie);
		if(hit&&hit.length>2) {
			return unescape(hit[2]);
		} else { 
			return ''; 
		}
	}
};

function set_cookie(name,value,days) {
	if(days) {
		var date = new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		var expires = "; expires="+date.toGMTString();
	} else {
		expires="";
	}
	document.cookie=name+"="+value+expires+"; path=/";
}

function get_password(name) {
	var pass = get_cookie(name);
	if(pass) {
		return pass;
	}

	var chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
	var pass = '';

	for(var i=0; i<8; i++) {
		var rnd = Math.floor(Math.random()*chars.length);
		pass += chars.substring(rnd,rnd+1);
	}

	return (pass);
}



function insert(text) {
	var textarea = document.forms.postform.nya2;
	if (textarea) {
		if(textarea.createTextRange && textarea.caretPos) { // IE
			var caretPos = textarea.caretPos;
			caretPos.text = caretPos.text.charAt(caretPos.text.length-1)==" "?text+" ":text;
		} else if(textarea.setSelectionRange) { // Firefox
			var start = textarea.selectionStart;
			var end = textarea.selectionEnd;
			textarea.value = textarea.value.substr(0,start)+text+textarea.value.substr(end);
			textarea.setSelectionRange(start+text.length,start+text.length);
		} else {
			textarea.value += text+" ";
		}
		textarea.focus();
	}
}

function highlight(post) {
	var cells = document.getElementsByTagName("td");
	for (var i=0; i<cells.length; i++) {
		if(cells[i].className == "highlight") {
			cells[i].className = "reply";
		}
	}

	var reply = document.getElementById("reply"+post);
	if (reply) {
		reply.className = "highlight";
/*		var match = /^([^#]*)/.exec(document.location.toString());
		document.location = match[1]+"#"+post;*/
		return false;
	}

	return true;
}

function set_stylesheet_frame(styletitle,tmp) {
	set_stylesheet(styletitle);
}

function set_stylesheet(styletitle,norefresh) {
	set_cookie("wakabastyle",styletitle,365);

	var links = document.getElementsByTagName("link");
	var found = false;
	for (var i=0; i<links.length; i++) {
		var rel = links[i].getAttribute("rel"),
			title = links[i].getAttribute("title");
		if (rel.indexOf("style") != -1 && title) {
			links[i].disabled = true; // IE needs this to work. IE needs to die.
			if (styletitle==title) {
				links[i].disabled = false;
				found = true;
			}
		}
	}
	if (!found) {
		set_preferred_stylesheet();
	}
}

function set_preferred_stylesheet() {
	var links = document.getElementsByTagName("link");
	for (var i=0; i<links.length; i++) {
		var rel = links[i].getAttribute("rel"),
			title = links[i].getAttribute("title");
		if (rel.indexOf("style")!=-1&&title) {
			links[i].disabled = (rel.indexOf("alt")!=-1);
		}
	}
}

function get_active_stylesheet()
{
	var links = document.getElementsByTagName("link");
	for (var i=0;i<links.length;i++) {
		var rel = links[i].getAttribute("rel"),
			title = links[i].getAttribute("title");
		if (rel.indexOf("style")!=-1 && title && !links[i].disabled) {
			return title;
		}
	}
	return null;
}

function get_preferred_stylesheet() {
	var links = document.getElementsByTagName("link");
	for (var i=0;i<links.length;i++) {
		var rel=links[i].getAttribute("rel"),
			title=links[i].getAttribute("title");
		if (rel.indexOf("style")!=-1&&rel.indexOf("alt")==-1&&title) {
			return title;
		}
	}
	return null;
}

function do_ban(el) {
	var reason = prompt("Give a reason for this ban:");
	if (reason) {
		document.location = el.href+"&comment="+encodeURIComponent(reason);
	}
	return false;
}

window.onunload=function(e) {
	if (style_cookie) {
		var title = get_active_stylesheet();
		set_cookie(style_cookie, title, 365);
	}
}

if(style_cookie) {
	var cookie = get_cookie(style_cookie),
		title = cookie?cookie:get_preferred_stylesheet();
	set_stylesheet(title);
}








var doc = document;
var postByNum = [];
var ajaxPosts = {};
var refArr = [];

function $X(path, root) {
	return doc.evaluate(path, root || doc, null, 6, null);
}
function $x(path, root) {
	return doc.evaluate(path, root || doc, null, 8, null).singleNodeValue;
}
function $del(el) {
	if(el) {
		el.parentNode.removeChild(el);
	}
}
function $each(list, fn) {
	if (!list) {
		return;
	}
	var i = list.snapshotLength;
	if(i > 0) {
		while(i--) {
			fn(list.snapshotItem(i), i);
		}
	}
}

function AJAX(b, id, fn) {
	var xhr = new XMLHttpRequest();
	xhr.onreadystatechange = function() {
		if(xhr.readyState != 4) return;
		if(xhr.status == 200) {
			var x = xhr.responseText;
			pNum = x.match(/<a[^>]+/).toString().match(/(?:")(\d+)(?:")/)[1];
			var wrapper= document.createElement('div');
			wrapper.innerHTML = x;
			postByNum[pNum] = wrapper;
			console.log(x);
			x = x.substring(x.indexOf('blockquote') + 12).match(/&gt;&gt;\d+/g);
			console.log(x);
			if (x) {
				for(var r = 0; rLen = x.length, r < rLen; r++) {
					getRefMap(x[r], pNum, x[r].replace(/&gt;&gt;/g, ''));
				}
			}

			//getRefMap
			//showRefMap(wrapper, pNum);
			/*
			var threads = x.substring(x.search(/<form[^>]+del/) + x.match(/<form[^>]+del[^>]+>/).toString().length, x.indexOf('userdelete">') - 13).split(/<br clear="left"[\s\/>]*<h[r\s\/]*>/i);
			for(var i = 0, tLen = threads.length - 1; i < tLen; i++) {
				var tNum = threads[i].match(/<input[^>]+checkbox[^>]+>/i)[0].match(/(?:")(\d+)(?:")/)[1];
				var posts = threads[i].split(/<table[^>]*>/);
				ajaxPosts[tNum] = {keys: []};
				for(var j = 0, pLen = posts.length; j < pLen; j++) {
					var x = posts[j];
					var pNum = x.match(/<input[^>]+checkbox[^>]+>/i)[0].match(/(?:")(\d+)(?:")/)[1];
					ajaxPosts[tNum].keys.push(pNum);
					ajaxPosts[tNum][pNum] = x.substring((!/<\/td/.test(x) && /filesize">/.test(x)) ? x.indexOf('filesize">') - 13 : x.indexOf('<label'), /<\/td/.test(x) ? x.lastIndexOf('</td') : (/omittedposts">/.test(x) ? x.lastIndexOf('</span') + 7 : x.lastIndexOf('</blockquote') + 13));
					x = ajaxPosts[tNum][pNum].substr(ajaxPosts[tNum][pNum].indexOf('<blockquote>') + 12).match(/&gt;&gt;\d+/g);
					if(x) for(var r = 0; rLen = x.length, r < rLen; r++) {
						getRefMap(x[r], pNum, x[r].replace(/&gt;&gt;/g, ''));
					}
				}
			}*/
			fn();
		} else fn('HTTP ' + xhr.status + ' ' + xhr.statusText);
	};
	//xhr.open('GET', '/threads/' + id + '.html', true);
	xhr.open('GET', '/threads/post/' + id + '.html', true);
	xhr.send(false);
}

function delPostPreview(e) {
	var el = $x('ancestor-or-self::*[starts-with(@id,"pstprev")]', e.relatedTarget);
	if(!el) {
		$each($X('.//div[starts-with(@id,"pstprev")]'), function(clone) {
				$del(clone); 
			});
	} else {
		while(el.nextSibling) {
			$del(el.nextSibling);
		}
	}
}

function showPostPreview(e) {
	var tNum = this.pathname.substring(this.pathname.lastIndexOf('/')).match(/\d+/);
    var pNum = this.hash.match(/\d+/) || tNum;
	var brd = this.pathname.match(/arch\/[^\/]+/);
	var x = e.clientX + (doc.documentElement.scrollLeft || doc.body.scrollLeft) - doc.documentElement.clientLeft + 1;
	var y = e.clientY + (doc.documentElement.scrollTop || doc.body.scrollTop) - doc.documentElement.clientTop;
	var cln = doc.createElement('div');
	cln.id = 'pstprev_' + pNum;
	cln.className = 'reply';
	cln.style.cssText = 'position:absolute; z-index:950; border:solid 1px #575763; top:' + y + 'px;' +
		(x < doc.body.clientWidth/2 ? 'left:' + x + 'px' : 'right:' + parseInt(doc.body.clientWidth - x + 1) + 'px');
	cln.addEventListener('mouseout', delPostPreview, false);
	var aj = ajaxPosts[tNum];
	var functor = function(cln, html) {
		cln.innerHTML = html;
		doRefPreview(cln);
		if(!$x('.//small', cln) && refArr[pNum]) {
			showRefMap(cln, pNum, tNum, brd);
		}
	};
	cln.innerHTML = 'Загружается...';
	if (postByNum[pNum]) {
		functor(cln, postByNum[pNum].innerHTML);
	} else {
		if (aj && aj[pNum]) {
			functor(cln, aj[pNum]);
		} else {
			AJAX(brd, pNum, function(err) {
				//functor(cln, err || ajaxPosts[tNum][pNum] || 'ааОбб аНаЕ аНаАаЙаДаЕаН')
				functor(cln, err || postByNum[pNum].innerHTML || 'ааОбб аНаЕ аНаАаЙаДаЕаН')
			})
		}
	}
	$del(doc.getElementById(cln.id));
	$x('.//form[@id="delform"]').appendChild(cln);
}

function doRefPreview(node) {
	$each($X('.//a[starts-with(text(),">>")]', node || doc), function(link) {
		link.addEventListener('mouseover', showPostPreview, false);
		link.addEventListener('mouseout', delPostPreview, false);
	});
}

function getRefMap(post, pNum, rNum) {
	console.log(pNum, rNum);
	if(!refArr[rNum]) {
		refArr[rNum] = pNum;
	} else {
		if(refArr[rNum].indexOf(pNum) == -1) {
			refArr[rNum] = pNum + ', ' + refArr[rNum];
		}
	}
}

function showRefMap(post, pNum, tNum, brd) {
	var ref = refArr[pNum].toString().replace(/(\d+)/g, 
	'<a href="' + (tNum ? '/arch/' + brd + '/res/' + tNum + '.html#$1' : '#$1') + '" onclick="highlight($1)">&gt;&gt;$1</a>');
	var map = doc.createElement('small');
	map.id = 'rfmap_' + pNum;
	map.innerHTML = '<br><i class="abbrev">&nbsp;Ответы: ' + ref + '</i><br>';
	doRefPreview(map);
	if(post) {
		post.appendChild(map);
	} else {
		var el = $x('.//a[@name="' + pNum + '"]');
		while(el.tagName != 'BLOCKQUOTE') { 
			el = el.nextSibling;
		}
		el.parentNode.insertBefore(map, el.nextSibling);
	}
}

function doRefMap() {
	$each($X('.//a[starts-with(text(),">>")]'), function(link) {
		if(!/\//.test(link.textContent)) {
			var rNum = link.hash.match(/\d+/);
			var post = $x('./ancestor::td', link);
			console.log('--', rNum, link, post);
			if((postByNum[rNum] || $x('.//a[@name="' + rNum + '"]')) && post) {
				getRefMap(post, post.id.match(/\d+/), rNum);
			}
		}
	});
	for(var rNum in refArr) {
		showRefMap(postByNum[rNum], rNum);
	}
}

function get_cookie(name) {
	with (document.cookie) {
		var regexp=new RegExp("(^|;\\s+)"+name+"=(.*?)(;|$)");
		var hit=regexp.exec(document.cookie);
		if (hit&&hit.length>2) {
			return unescape(hit[2]);
		} else {
			return '';
		}
	}
};

function set_cookie(name,value,days) {
	if (days) {
		var date=new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		var expires="; expires="+date.toGMTString();
	} else {
		expires="";
	}
	document.cookie=name+"="+value+expires+"; path=/";
}

function get_password(name)
{
	var pass=get_cookie(name);
	if(pass) return pass;

	var chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
	var pass='';

	for(var i=0;i<8;i++)
	{
		var rnd=Math.floor(Math.random()*chars.length);
		pass+=chars.substring(rnd,rnd+1);
	}

	return(pass);
}

function update_captcha(e)
{
    e.src = e.src.replace(/dummy=[0-9]*/, "dummy=" + Math.floor(Math.random() * 1000).toString());
}

function update_captcha2()
{
    var e = document.getElementById('imgcaptcha');
    if (e) update_captcha(e);
}

function get_frame_by_name(name)
{
	var frames = window.parent.frames;
	for(i = 0; i < frames.length; i++)
	{
		if(name == frames[i].name) { return(frames[i]); }
	}
}

function lazyadmin()
{
    var admin=get_cookie("wakaadmin");
    if(!admin){
        return ;
    }
    var posts = document.getElementsByClassName('reflink');
    var post;
    var id;
    var pos;
    var tmp;
    var board=document.location.toString().split("/")[3];
    for(var i=0;i<posts.length;i++) {
        post = posts[i];
        //This is wrong, but monkey cannot Regexp.
        pos=post.innerHTML.indexOf('т');
        pos=post.innerHTML.length;
        //console.log(post.innerHTML+"\n"+pos);
        if(pos>0)
        {
            tmp=post.innerHTML.substring(pos+1);
            id=tmp.substring(0,tmp.indexOf('<'));
			post.innerHTML+="[ <a title=\"аЃаДаАаЛаИбб ббаО баОаОаБбаЕаНаИаЕ\" href=\"/"+board+"/wakaba.pl?task=delete&admin="+admin+"&delete="+id+"&mode=2\">D</a> | ";
            post.innerHTML+="<a title=\"ааАаБаАаНаИбб аАаВбаОбаА\" href=\"/"+board+"/wakaba.pl?admin="+admin+"&task=banpost&post="+id+"&mode=3\" onclick=\"return do_ban(this)\">B</a> | ";
			post.innerHTML+="<a title=\"ааАаБаАаНаИбб аАаВбаОбаА аИ баДаАаЛаИбб ббаО баОаОаБбаЕаНаИаЕ\" href=\"/"+board+"/wakaba.pl?admin="+admin+"&task=banpost&post="+id+"&mode=1\" onclick=\"return do_ban(this)\">D&B</a> | ";
			post.innerHTML+="<a title=\"аЃаДаАаЛаИбб аВбаЕ баОаОаБбаЕаНаИб ббаОаГаО аАаВбаОбаА\" href=\"/"+board+"/wakaba.pl?task=banpost&admin="+admin+"&post="+id+"&mode=5\">DAll</a> | ";
            post.innerHTML+="<a title=\"ааАаБаАаНаИбб аАаВбаОбаА аИ баДаАаЛаИбб аВбаЕ аЕаГаО баОаОаБбаЕаНаИб\" href=\"/"+board+"/wakaba.pl?admin="+admin+"&task=banpost&post="+id+"&mode=6\" onclick=\"return do_ban(this)\">DAll&B</a> | ";
            post.innerHTML+="<a title=\"аЃаДаАаЛаИбб баАаЙаЛ аИаЗ баОаОаБбаЕаНаИб\" href=\"/"+board+"/wakaba.pl?task=delete&admin="+admin+"&delete="+id+"&fileonly=on&mode=2\">F</a> | ";
			post.innerHTML+="<a title=\"ааЕбаЕаНаЕббаИ аВ аАббаИаВ\" href=\"/"+board+"/wakaba.pl?task=delete&admin="+admin+"&archive=Archive&mode=2&delete="+id+"\">A</a> ]";
        
		}

    }
}

function do_ban(el) {
	var reason=prompt("Give a reason for this ban:");
	if(reason) {
		document.location=el.href+"&comment="+encodeURIComponent(reason);
	}
	return false;
}

window.onload=function(e) {
	var match;

	if(match=/#i([0-9]+)/.exec(document.location.toString())) {
		if(!document.forms.postform.shampoo.value) {
			insert(">>"+match[1]);
		}
	}
	if(match=/#([0-9]+)/.exec(document.location.toString())) {
		highlight(match[1]);
	}

	lazyadmin();

	$each($X('.//td[@class="reply"]'), function(post) {
			postByNum[post.id.match(/\d+/)] = post
		});
	doRefPreview();
	doRefMap();
}


function expand(self,src,n_w,n_h,o_w,o_h) {
	var element = document.getElementById(self);
	var ssrc="'"+src+"'";
	var sself="'"+self+"'";
	var link="<a href=\"#\" onClick=\"expand("+sself+","+ssrc+","+o_w+","+o_h+","+n_w+","+n_h+"); return false;\">" ;
	var img="<img src=\""+src+"\" width=\""+n_w+"\" height=\""+n_h+"\" class=\"thumb\" >";
	element.innerHTML=link+img;

}
