# -*- coding:utf-8 -*-

import socket
import socketserver
import threading
import queue
import logging, logging.handlers
import os, sys
import time

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import utils
import models

class SdkReceiverHander(socketserver.StreamRequestHandler):

	_key = None
	_dispatched_jobs = []
	_results = []

	def _info(self, msg):
		logging.info("(%s:%s): %s" % (self.client_address[0], self.client_address[1], msg))
		
	def _error(self, msg):
		logging.error("(%s:%s): %s" % (self.client_address[0], self.client_address[1], msg))
		
	def handle(self):
		#print('Client: ', self.client_address)
		while True:
			# obj = getData(self.connection)
			# self.protocol(obj)
			try:
				obj = utils.getData(self.connection)
				if obj is None:
					break
				self.protocol(obj)
			except:
				import traceback
				# traceback.print_exc()
				self.resend()
				self._error("exception, exit!")
				break

	def resend(self):
		q = self.server._multi_tasks.get(self._key)
		for i in self._dispatched_jobs:
			self._info("recycle cases: %s, %s" % (i.case, i.version))
			q.put(i)
				
	def send_data(self, data):
		return self.request.sendall(utils.makePickle(data))

	def protocol(self, data):
		method = getattr(self, 'handle_%s' % data.head, None)
		if method is None:
			self._error("%s handle not exist." % data.head)
			raise ValueError("%s handle not exist." % data.head)
		method(data)

	def handle_register_uut_key(self, data):
		self._key = ','.join([data.cmodel_branch, data.driver_branch, data.chip])
		self._info("register key: %s" % self._key)

		with self.server._lock:
			if self.server._multi_tasks.get(self._key, None) is None:
				self._info("======== Init key: %s" % self._key)
				self.server._multi_tasks[self._key] = queue.Queue()
				self.set_version(self._key, self.server._multi_tasks[self._key])
			else:
				version = self.server._key_versions_map.get(self._key)
				self._info("==== Send case for version: %s" % version)
			if self.server._lower_tasks.get(self._key, None) is None:
				self.server._lower_tasks[self._key] = queue.Queue()
				
	def handle_get_task(self, data):
		q = self.server._multi_tasks.get(self._key, None)
		if q is None:
			self._error("Can not find task for %s, Please register first" % self._key)
			raise RuntimeError("can not find cases for %s" % self._key)
		with self.server._lock:
			if q.empty():
				self.set_version(self._key, q)
			version = self.server._key_versions_map.get(self._key)
			tmp = q.get()

		if isinstance(tmp, models.Transport):
			obj = tmp
		else:
			obj = models.Transport("case")
			obj.case = tmp
			obj.version = version
		self._info("send case (%s, %s)" % (obj.case, obj.version))
		self.send_data(obj)
		self._dispatched_jobs.append(obj)

	def handle_result(self, data):
		if not data.finish:
			obj = models.Transport("case")
			obj.case = data.case
			obj.version = data.version
			self.server._lower_tasks[self._key].put(obj)
			return
		for i in range(len(self._dispatched_jobs)):
			obj = self._dispatched_jobs[i]
			if obj.version == data.version:
				if str(obj.case) == data.case:
					self._dispatched_jobs.remove(obj)
					self._info("recieved result: %s, %s" %(obj.case, obj.version))
					break

	def set_version(self, key, queue):
		tmp = key.split(',')
		version = utils.get_sdk_version(tmp[2], tmp[1], tmp[0])
		while version is None:
			try:
				obj = self.server._lower_tasks[key].get_nowait()
			except:
				self._info("==== No new version, sleep 2 min")
				time.sleep(120)
				version = utils.get_sdk_version(tmp[2], tmp[1], tmp[0])
				continue
			self.server._multi_tasks[key].put(obj)
			return
			
		self._info("==== Start to send case for version: %s" % version)
		self.server._key_versions_map[key] = version
		utils.dispatch_tasks(tmp[2], queue)

class TestingSocketServer(socketserver.ThreadingTCPServer):

	allow_reuse_address = True
	request_queue_size	= 20

	def __init__(self, host='localhost', port=0, handler=SdkReceiverHander):
		socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)

		self._lock = threading.Lock()
		self._multi_tasks = dict()
		self._lower_tasks = dict()
		self._key_versions_map = dict()
		
		logging.basicConfig(
			level=logging.DEBUG,
			format='[%(levelname)s] [%(asctime)s]: %(message)s'
			)

		result_dir = 'A:\\results\\autotest'
		if not os.path.exists(result_dir):
			os.system('md %s' % result_dir)
		handler = logging.handlers.RotatingFileHandler(
				os.path.join(result_dir, 'server.log'),
				'a', 10*1024*1024, 10
				)
		fmt		= logging.Formatter('[%(levelname)-8s] [%(asctime)-15s] [%(thread)d]: %(message)s')
		handler.setFormatter(fmt)
		logging.getLogger().addHandler(handler)

if __name__ == '__main__':
	tcpserver = TestingSocketServer()
	print('About to start TCP server...')
	tcpserver.serve_forever()

