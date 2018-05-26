
import os, sys
import logging
import logging.handlers
import socketserver

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import utils

class LogRecordStreamHandler(socketserver.StreamRequestHandler):

	def handle(self):
		# print('Client: ', self.client_address)
		self.logger = logging.getLogger()
		while True:
			try:
				data = utils.getData(self.connection)
				if data is None:
					break
			except:
				import traceback
				# self.logger.error(traceback.format_exc())
				# traceback.print_exc()
				break
			record = logging.makeLogRecord(data)
			self.handleLogRecord(record)

	def handleLogRecord(self, record):
		record.ip = self.client_address
		self.set_log_format(record.name)
		self.logger = logger = logging.getLogger(record.name)
		logger.handle(record)

	def set_log_format(self, name):
		if name == '' or name in self.server.log_handlers:
			return
		tmp = name.split(',')
		if len(tmp) == 4:
			path = os.sep.join(['A:\\results\\autotest'] + tmp)
			log_file = os.path.join(path, 'trace.log')
		elif len(tmp) == 3:
			path = os.path.join('A:\\results\\autotest', tmp[0], tmp[1])
			log_file = os.path.join(path, 'trace_%s.log'%tmp[2])
		else:
			return
		
		self.server.log_handlers.append(name)
		if not os.path.exists(path):
			os.system('md %s' % path)
		fmt = logging.Formatter('[%(levelname)-8s] [%(asctime)-15s] [IP: %(ip)-15s] [%(process)d(%(thread)d)]: %(message)s')
		file_handler = logging.FileHandler(log_file)
		file_handler.setFormatter(fmt)
		logger = logging.getLogger(name)
		logger.addHandler(file_handler)
		logger.setLevel(logging.DEBUG)

class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):

	allow_reuse_address = True
	request_queue_size	= 20

	def __init__(self, host='localhost',
				port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
				handler=LogRecordStreamHandler):
		socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)

		self.log_handlers = []

def start_server(ip):
	logging.basicConfig(
			level=logging.DEBUG,
			format='[%(levelname)s] [%(asctime)s] [IP: %(ip)s]: %(message)s'
			)

	result_dir = 'A:\\results\\autotest'
	if not os.path.exists(result_dir):
		os.system('md %s' % result_dir)
	handler = logging.handlers.RotatingFileHandler(
			os.path.join(result_dir, 'test.log'),
			'a', 10*1024*1024, 10
			)
	fmt		= logging.Formatter('[%(levelname)-8s] [%(asctime)-15s] [IP: %(ip)-15s] [%(process)d(%(thread)d)]: %(message)s')
	handler.setFormatter(fmt)
	logging.getLogger().addHandler(handler)

	server	= LogRecordSocketReceiver(host=ip)
	print('Start logger server... at ', server.socket.getsockname())
	server.serve_forever()

if __name__ == '__main__':
	start_server()
