import sys
import os
if sys.version_info[0]<3:       # require python3
 raise Exception("Python3 required! Current (wrong) version: '%s'" % sys.version_info)
sys.path.insert(0, '/var/www/goujer.com/kanojo/')
from web_job import app as application
