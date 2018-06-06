
import os, sys
import socket
import time
import multiprocessing as mp
import threading
import logging, logging.handlers

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import reloader
from utils import *

class Client(object):

	def __init__(self, processes=None, cmodel_branch=None, driver_branch=None, chip=None):
		if cmodel_branch is None or driver_branch is None or chip is None:
			raise ValueError("cmodel or driver branch or chip is error")
		self._cmodel_branch = cmodel_branch
		self._driver_branch = driver_branch
		self._chip = chip

		if processes is None:
			processes = os.cpu_count() or 1
		if processes < 1:
			raise ValueError("Number of processes must be at least 1")

		self._work_semaphore = mp.Semaphore(processes)
		self._processes = processes
		self._log_msgs = mp.Queue(-1)
		self._results = mp.Queue(-1)

		ser = "A:\\cmodel_driver\\autobuilds\\server"
		if not os.path.exists(ser):
			raise RuntimeError("Can not get server. Please start server first.")
		with open(ser, 'r') as f:
			line = f.readlines()[0].strip().split()
		
		self._server_ip = line[0]
		self._server_port = int(line[1])
		
		manager = mp.Manager()
		self._slow_jobs = manager.list()
		self._mutex = mp.Lock()

	def logging_listener(self):
		rootLogger = logging.getLogger('')
		rootLogger.setLevel(logging.DEBUG)
		socketHandler = logging.handlers.SocketHandler(self._server_ip, logging.handlers.DEFAULT_TCP_LOGGING_PORT)
		rootLogger.addHandler(socketHandler)
		while True:
			try:
				record = self._log_msgs.get()
				if record is None:
					break
				logger = logging.getLogger(record.name)
				logger.handle(record)
			except Exception:
				import traceback
				traceback.print_exc(file=sys.stderr)

	def logging_configure(self):
		h = logging.handlers.QueueHandler(self._log_msgs)
		root = logging.getLogger()
		root.addHandler(h)
		root.setLevel(logging.DEBUG)

	def test_process(self, version, jobs):
		self.logging_configure()
		logger = logging.getLogger(','.join([self._cmodel_branch, self._driver_branch, version, self._chip]))
		logger.info("======== start test version: %s ========" % version)
		tester = Tester(cmodel_branch=self._cmodel_branch, driver_branch=self._driver_branch, chip=self._chip, version=version)
		tester.init_test()
		threads = []
		for i in range(self._processes):
			t = threading.Thread(target=self.run, args=(jobs, tester, version, logger, ))
			threads.append(t)

		for t in threads:
			t.start()

		for t in threads:
			t.join()
		logger.info("======== end test version: %s ========" % version)

	def run(self, jobs, tester, version, logger):
		with self._work_semaphore:
			while True:
				job = jobs.get()
				if job is None:
					logger.info("====: No task, exit this thread! ====")
					break
				if job.is_exists():
					with self._mutex:
						if str(job) in self._slow_jobs:
							logger.info("Other instance of %s is running, skipped at temporary!")
							self._results.put([str(job), version, False])
							continue
						else:
							self._slow_jobs.append(str(job))
				try:
					tester.run(job)
					self._results.put([str(job), version, True])
				except:
					import traceback
					traceback.print_exc(file=sys.stderr)
					logger.error(traceback.format_exc())

	def start_test(self, version):
		jobs = mp.Queue(self._processes+2)
		test = mp.Process(target=self.test_process, args=(version, jobs, ))
		test.start()

		return (jobs, test)

	def get_jobs(self):
		self.logging_configure()
		logger = logging.getLogger(','.join([self._cmodel_branch, self._driver_branch, self._chip]))
		
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((self._server_ip, self._server_port))
		logger.info("========: Connected to server (%s, %s)" % (self._server_ip, self._server_port))

		t = threading.Thread(target=self.send_results, args=(sock, ))
		t.start()
		
		obj = Transport('register_uut_key')
		obj.cmodel_branch = self._cmodel_branch
		obj.driver_branch = self._driver_branch
		obj.chip = self._chip	
		sock.sendall(makePickle(obj))
		logger.info("Init test unit: %s, %s, %s" % (self._cmodel_branch, self._driver_branch, self._chip))

		cur_version = None
		jobs = None
		procs = []
		
		while True:
			obj = Transport('get_task')
			sock.sendall(makePickle(obj))
			data = getData(sock)
			if data is None:
				break
			if data.head == 'case':
				if data.version != cur_version:
					logger.info("====:receive version: %s" % data.version)
					cur_version = data.version
					if jobs:
						for i in range(self._processes):
							jobs.put(None)
					(jobs, p) = self.start_test(data.version)
					procs.append(p)
				logger.info("receive case: %s %s" % (data.case, data.version))
				jobs.put(data.case)

		for p in procs:
			p.join()

		t.join()
			
	def send_results(self, sock):
		while True:
			ret = self._results.get()
			if ret is None:
				break
			obj = Transport('result')
			obj.case = ret[0]
			obj.version = ret[1]
			obj.finish = ret[2]
			sock.sendall(makePickle(obj))

	def start(self):
		#	start logging listener
		plog = mp.Process(target = self.logging_listener)
		plog.start()

		#	start get tasks from server
		pjob = threading.Thread(target = self.get_jobs)
		pjob.start()
		

		pjob.join()
		self._results.put_nowait(None)
		self._log_msgs.put_nowait(None)
		plog.join()

def load_modify():
	loader = reloader.Reloader()
	while True:
		time.sleep(60)
		loader()

if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser()
	
	parser.add_argument('driver_branch', help='driver branch want to test')
	parser.add_argument('chip', help='which cmodel want to test')
	parser.add_argument('--cmodel_branch', default='projects.v620_v2', help="cmodel branch want to test")
	parser.add_argument('-p', '--thread_num', type=int, default=os.cpu_count(), help='parallel running numbers. Default is cpu core count')

	args = parser.parse_args()

	# start auto load function when modules was updated
	ploader = mp.Process(target=load_modify)
	ploader.start()

	client = Client(args.thread_num, args.cmodel_branch, args.driver_branch, args.chip)
	client.start()
