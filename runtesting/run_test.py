import os, sys
import threading
import logging
import queue

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import *
import utils

class ContextFilter(logging.Filter):
	def filter(self, record):
		record.ip = utils.get_host_ip()
		return True
		
def config_logger(path):
	SHELL.call("md %s" % path)
	log_file = os.path.join(path, 'trace.log')
	logging.basicConfig(
		level=logging.DEBUG, 
		format='[%(levelname)-8s] [%(asctime)-15s] [IP: %(ip)-14s] [%(process)d(%(thread)d)]: %(message)s',
		datefmt='%Y.%m.%d %H:%M:%S',
		filename=log_file,
		filemode='a',
	)
	console = logging.StreamHandler()
	console.setLevel(logging.WARNING)
	formatter = logging.Formatter('[%(levelname)s] [%(asctime)s] [%(process)d(%(thread)d)]: %(message)s')
	console.setFormatter(formatter)
	logging.getLogger().addHandler(console)
	
	tmp = path.split(os.sep)
	logger = logging.getLogger(','.join(tmp[-4:]))
	f = ContextFilter()	 
	logger.addFilter(f)
	return logger
	
def get_tasks(task_file, max_num):
	tasks = []
	with open(task_file, 'r') as f:
		lines = f.readlines()
	for i in range(len(lines)):
		line = lines[i].strip()
		if line == '':
			continue
		if line.startswith('#'):
			continue
		if line.startswith('nn unit_test'):
			lines[i] = '#' + line + '\n'
			tasks.append(line)
			break
		tasks.append(line)#未执行的case放入到tasks
		lines[i] = '#' + line + '\n'
		if len(tasks) == max_num:
			break	
	with open(task_file, 'w') as f:#运行了case之后，需要更新task_file中的状态
		f.writelines(lines)
		
	return tasks
		
def get_jobs(task_file, jobs, max_num):
	while True:
		tasks = get_tasks(task_file, max_num)
		if len(tasks) == 0:
			for i in range(max_num):
				jobs.put(None)
			break
		for task in tasks:
			tmp = task.split()
			if len(tmp) < 2:
				continue
			category = tmp[0]
			name = tmp[1]
			c_args = ' '.join(tmp[2:])
			if category == 'nn':
				if name.startswith('unit_test'):
					utils.dispatch_nn_unit_tasks(jobs, category, name, c_args)
				else:
					jobs.put(NN_case(category, name, c_args))
			elif category.startswith('ocl'):
				if name.startswith('cts'):
					utils.dispatch_ocl_cts_tasks(jobs, category, name, c_args)
			else:
				jobs.put(NN_case(category, name, c_args))
				
def run(jobs, tester):
	while True:
		job = jobs.get()
		if job is None:
			break
		tester.run(job)
	
#  main
if __name__ == '__main__':

	import argparse
	parser = argparse.ArgumentParser()

	parser.add_argument('driver', help='driver directory need to test, which saved dlls')
	parser.add_argument('-t', '--task_file', help='The task list file, default run the list in cases saved directory')
	parser.add_argument('-p', '--thread_num', type=int, default=os.cpu_count(), help='parallel numbers')

	args = parser.parse_args()
	assert args.driver
	assert os.path.exists(args.driver)
	
	tester = Tester(driver=args.driver)#获取相关的drv，cmodel版本信息，及存储位置
	tester._logger = config_logger(tester._savedir)#配置日志信息
	tester.init_test()#设置相关环境变量
	
	task_file = args.task_file
	if task_file is None:
		task_file = os.path.join(tester._savedir, 'task.txt')
	else:
		assert os.path.exists(task_file)
	if not os.path.exists(task_file):
		if os.path.exists('%s\\task_%s.txt' % (CASE_HOME, tester._chip)):
			SHELL.call('copy /y %s\\task_%s.txt %s' % (CASE_HOME, tester._chip, task_file))
		else:
			SHELL.call('copy /y %s\\default_task.txt %s' % (CASE_HOME, task_file))
			
	jobs = queue.Queue(args.thread_num+2)
	
	threads = []
	t = threading.Thread(target=get_jobs, args=(task_file, jobs, args.thread_num+2, ))#Thread的run方法将调用get_jobs，args将作为get_jobs的调用参数
	t.start()
	threads.append(t)

	for i in range(args.thread_num):
		t = threading.Thread(target=run, args=(jobs, tester, ))
		t.start()
		threads.append(t)

	for t in threads:
		t.join()