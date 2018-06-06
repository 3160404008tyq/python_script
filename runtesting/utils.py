
import pickle
import struct
import glob
import os, sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import *
		
def get_host_ip():
	import socket

	ip = 'localhost'
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 80))
		ip = s.getsockname()[0]
	finally:
		s.close()

	return ip
	
def makePickle(obj):
	s		= pickle.dumps(obj, 1)
	slen	= struct.pack(">L", len(s))
	return slen + s

def getData(socket):
	chunk = socket.recv(4)
	if not chunk or len(chunk) < 4:
		return None
	slen = struct.unpack('>L', chunk)[0]
	chunk = socket.recv(slen)
	while len(chunk) < slen:
		chunk = chunk + socket.recv(slen - len(chunk))
	return pickle.loads(chunk)
	
def get_sdk_version(chip, drv_branch, cmodel_branch='projects.v620_v2'):
	version = None
	if not chip.startswith('gcDefines_'):
		chip = 'gcDefines_' + chip
	file = os.path.join(SDK_HOME, cmodel_branch, drv_branch, chip+'.txt')
	with open(file, 'r') as f:
		lines = f.readlines()
		for i in range(SDK_VERSIONS):
			line = lines[i].strip()
			if not line:
				break
			if line.startswith('#'):
				continue
			version = line
			lines[i] = '#' + line + '\n'
			break
	with open(file, 'w') as f:
		f.writelines(lines)

	return version
	
def dispatch_nn_unit_tasks(queue, category, name, c_args):#装载case
	import re

	path = os.path.join(CASE_HOME, category, name)
	tp = None
	m = re.search(r'\-r\s+(?P<type>\w+)', c_args)#(?P<type>\w+)正则表达式中的分组，并将组名命名为type
	if m:
		tp = m.group('type')
		
	if tp is None:
		for i in glob.glob(os.path.join(path, '*', '*', '*.exe')):#glob.glob返回所有匹配的文件路径列表
			t = i.split(os.sep)
			queue.put(NN_unit_case(category, name, t[-3], t[-2]))#t[-3], t[-2])是case的外层文件夹
		return
		
	file = os.path.join(path, 'list_%s.txt'%tp)
	if not os.path.exists(file):
		raise ValueError("%s is not exist" % file)
	with open(file, 'r') as f:
		tasks = f.readlines()
	for i in tasks:
		if i.strip() == '':
			continue
		tmp = i.strip().split()
		if len(tmp) > 1:	
			queue.put(NN_unit_case(category, name, tmp[0], tmp[1]))
		else:
			bins = glob.glob(os.path.join(path, '*', tmp[0]))
			group = os.path.basename(os.path.dirname(bins[0]))
			queue.put(NN_unit_case(category, name, group, tmp[0]))
			
def dispatch_ocl_cts_tasks(queue, category, name, c_args):
	if c_args == '':
		c_args = 'suquick'
	file = os.path.join(CASE_HOME, category, name, c_args + '.txt')
	with open(file, 'r') as f:
		lines = f.readlines()
	for line in lines:
		line = line.strip()
		tmp = line.split()
		if len(tmp) == 1:
			queue.put(Ocl_cts_case(category, name, tmp[0]))
		else:
			queue.put(Ocl_cts_case(category, name, tmp[0], ' '.join(tmp[1:])))
	
def dispatch_tasks(chip, queue, task_file=None):
	if task_file is not None and os.path.exists(task_file):
		file = task_file
	else:
		chip_task = os.path.join(CASE_HOME, 'task_%s.txt' % chip)
		if os.path.exists(chip_task):
			file = chip_task
		else:
			file = os.path.join(CASE_HOME, 'default_task.txt')
			
	with open(file, 'r') as f:
		lines = f.readlines()
	for line in lines:
		line = line.strip()
		if line.startswith('#'):
			continue
		tmp = line.split()
		if len(tmp) < 2:
			continue
		category = tmp[0]
		name = tmp[1]
		c_args = ' '.join(tmp[2:])
		if category == 'nn':
			if name.startswith('unit_test'):
				dispatch_nn_unit_tasks(queue, category, name, c_args)
			else:
				queue.put(NN_case(category, name, c_args))
		elif category.startswith('ocl'):
			if name.startswith('cts'):
				dispatch_ocl_cts_tasks(queue, category, name, c_args)
		elif category.startswith('ovx'):
			pass
		else:
			queue.put(NN_case(category, name, c_args))
			
