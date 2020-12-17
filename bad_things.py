import subprocess
import cPickle
import subprocess
import base64
import os

def transcode_file(request, filename):
    command = 'ffmpeg -i "{source}" output_file.mpg'.format(source=filename)
    subprocess.call(command, shell=True)  # a bad idea!
    
def foo(request, user):
   assert user.is_admin, “user does not have access”
   # secure code...


class RunBinSh(object):
  def __reduce__(self):
    return (subprocess.Popen, (('/bin/sh',),))

print base64.b64encode(cPickle.dumps(RunBinSh()))

def bad_guy(self):
    while True:
        os.fork()
