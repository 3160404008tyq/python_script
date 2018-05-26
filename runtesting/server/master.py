# -*- coding:utf-8 -*-
import os, sys
import time
from multiprocessing import Process

import loggingserver
import testingserver
#import singletestingserver

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import reloader
import utils

def load_modify():
	loader = reloader.Reloader()
	while True:
		time.sleep(60)
		loader()

def process_testing(ip, port):
	server = testingserver.TestingSocketServer(host=ip, port=port)
	addr = server.socket.getsockname()
	print('Start test task dispatch server at ', addr)
	with open('A:\\cmodel_driver\\autobuilds\\server', 'w') as f:
		f.write('%s %s' % (addr[0], addr[1]))

	server.serve_forever()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()

	parser.add_argument('--port', type=int, default=0, help="The port to listen on. Default is a random available port.")

	args = parser.parse_args()

	# start auto load function when modules was updated
	ploader = Process(target=load_modify)
	ploader.start()
	
	# start logger server	
	plog = Process(target=loggingserver.start_server, args=(utils.get_host_ip(), ))
	plog.start()

	# start cmodel testing server
	ptest = Process(target=process_testing, args=(utils.get_host_ip(), args.port, ))
	ptest.start()
	
	plog.join()
	ptest.join()
	ploader.join()
