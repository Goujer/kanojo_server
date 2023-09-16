// AJAX object
var ajax = {};
ajax.x = function() {
    if (typeof XMLHttpRequest !== 'undefined') {
        return new XMLHttpRequest();  
    }
    var versions = [
        "MSXML2.XmlHttp.6.0",
        "MSXML2.XmlHttp.5.0",   
        "MSXML2.XmlHttp.4.0",  
        "MSXML2.XmlHttp.3.0",   
        "MSXML2.XmlHttp.2.0",  
        "Microsoft.XmlHttp"
    ];

    var xhr;
    for(var i = 0; i < versions.length; i++) {  
        try {  
            xhr = new ActiveXObject(versions[i]);  
            break;  
        } catch (e) {
        }  
    }
    return xhr;
};
ajax.send = function(url, callback, method, data, sync) {
    var x = ajax.x();
    x.open(method, url, sync);
    x.onreadystatechange = function() {
        if (x.readyState == 4) {
            callback(x.responseText)
        }
    };
    if (method == 'POST') {
        x.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    }
    x.send(data)
};
ajax.get = function(url, data, callback, sync) {
    var query = [];
    for (var key in data) {
        query.push(encodeURIComponent(key) + '=' + encodeURIComponent(data[key]));
    }
    ajax.send(url + (query.length ? '?' + query.join('&') : ''), callback, 'GET', null, sync)
};
ajax.post = function(url, data, callback, sync) {
    var query = [];
    for (var key in data) {
        query.push(encodeURIComponent(key) + '=' + encodeURIComponent(data[key]));
    }
    ajax.send(url, callback, 'POST', query.join('&'), sync)
};

/* Update time on Last Activities */
function update_time(arr) {
  function val_str(val, suffix) {
    var rv = val + ' ' + suffix;
    if (val > 1) {
      rv += 's';
    }
    return rv;
  }

  var i, el, val,
      curr_time = Math.round(new Date().getTime()/1000.0);
  for (i=0; i<arr.length; i++) {
    el = arr[i].lastChild.lastChild;
    val = curr_time - el.getAttribute('value');
    if (val < 60) {
      val = 'less than minute';
    } else {
      val = Math.floor(val / 60);
      if (val < 60) {
        val = val_str(val, 'min');
      } else {
        val = Math.floor(val / 60);
        if (val < 24) {
          val = val_str(val, 'hour');
        } else {
          val = Math.floor(val / 24);
          if (val < 7) {
            val = val_str(val, 'day');
          } else {
            val = val / 7;
            if (val < 5) {
              val = val_str(Math.floor(val), 'week');
            } else {
              val = Math.floor(val * 7 / 30.5);
              if (val < 12) {
                val = val_str(val, 'year');
              }
            }
          }
        }
      }
    }
    el.innerHTML = '@ ' + val + ' ago';
  }
}
