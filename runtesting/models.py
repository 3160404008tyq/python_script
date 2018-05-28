
import os, sys
import configparser
import logging
import threading
import subprocess
import shutil
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import *
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utility.sys_call import SHELL
import utility.utils as UT

class Transport(object):
	"""
	message to transport
	"""
	def __init__(self, head):
		self.head = head
		
class NN_case(object):
	def __init__(self, category, name, c_args=''):
		self._category	= category
		self._name		= name
		self._c_args	= c_args
		self._timeout	= 3*24*3600	
		
	def __str__(self):
		return ' '.join([self._category, self._name, self._c_args])
		
	@property
	def key(self):
		return self._name
		
	@property
	def cmdline(self):
		return "run.bat %s" % self._c_args
		
	@property
	def bin(self):
		run = os.path.join(CASE_HOME, self._category, self._name, 'run.bat')
		with open(run, 'r') as f:
			lines = f.readlines()
		return lines[0].split()[0]
		
	@property
	def case_path(self):
		path = os.path.join(CASE_HOME, self._category, os.environ.get('HW_CONFIG'), self._name)
		if not os.path.exists(path):
			path = os.path.join(CASE_HOME, self._category, self._name)
		return path
		
	@property
	def result_path(self):
		return os.path.join(self.tester._savedir, self._category, self._name)
		
	@property
	def work_path(self):
		return os.path.join(self.tester._workdir, self._category, self._name)
		
	def _info(self, msg):
		msg = "%s: %s" % (self.key, msg)
		logger = getattr(self.tester, '_logger', logging.getLogger())
		logger.info(msg)

	def _error(self, msg):
		msg = "%s: %s" % (self.key, msg)
		logger = getattr(self.tester, '_logger', logging.getLogger())
		logger.error(msg)
		
	def is_exists(self):
		try:
			SHELL.check_call("tasklist /fo csv | find /i \"%s.exe\"" % self.bin)
		except:
			return False	
		return True
		
	def append_workdir(self):
		if self.is_exists():
			index = 1
			workdir = '%s_%s'% (self.work_path, index)
			while os.path.exists(workdir):
				index += 1
				workdir = '%s_%s'% (self.work_path, index)
			delete = True
		else:
			workdir = self.work_path
			delete = False
		SHELL.call("md %s" % workdir)
		return (workdir, delete)
		
	def get_case_type(self):
		tf = False
		if self.key.find('_tf_') != -1 or self.bin.find('asymmetricquantizedu8') != -1:
			tf = True
		if self.key.find('_int16') != -1:
			return (tf, 'int16')
		if self.key.endswith('int8') or self.key.find('_int8_') != -1:
			return (tf, 'int8')
		return (tf, 'fp16')
		
	def coveraged_case(self):
		(tf, tp) = self.get_case_type()
		if os.environ.get('HW_IS_SUPPORT_INT8', '1') == '0' and tp is 'int8':
			return False
		if os.environ.get('HW_IS_SUPPORT_FP16', '1') == '0' and tp is 'fp16':
			return False
		if os.environ.get('HW_IS_SUPPORT_INT16', '1') == '0' and tp is 'int16':
			return False
		if os.environ.get('HW_IS_SUPPORT_TF_QUANTIZATION', '1') == '0' and tf:
			return False
		if self.key in CHIP_IGNORES.get(self.tester._chip, IGNORES):
			return False
		return True
		
	def install_case(self, dst):
		UT.incr_copy(self.case_path, dst)
		SHELL.call('xcopy /y %s\\cl_viv_vx_ext.h %s\\'%(self.tester._local_driver, dst))
		self._info("Finish install cases")
		
	def copy_cfg_files(self):
		SHELL.call('xcopy /y %s\\*.ini %s\\' % (self.tester._local_driver, self.result_path))
		SHELL.call('xcopy /y %s\\golden.txt %s\\' % (self.case_path, self.result_path))
		SHELL.call('xcopy /y %s\\*.ini %s\\' % (self.case_path, self.result_path))
		SHELL.call('xcopy /y %s\\check_result.py %s\\' % (self.case_path, self.result_path))
		SHELL.call('xcopy /s/y/i %s\\golden\\* %s\\golden\\' % (self.case_path, self.result_path))
	
	def record_case_info(self):
		case_info = os.path.join(self.result_path, 'case_info.ini')
		try:
			i_parser = configparser.ConfigParser()
			i_parser.read(case_info)
			if not i_parser.has_section(self._name):
				i_parser.add_section(self._name)
			i_parser.set(self._name, 'category', self._category)
			i_parser.set(self._name, 'args', self._c_args)
			i_parser.write(open(case_info, 'w'))
		except:
			pass
	
	def record_environment(self):
		with open(os.path.join(self.result_path, 'cfg.ini'), 'a') as f:
			f.write('\n[env]\n')
			for (n, v) in os.environ.items():
				f.write('\n%s=%s\n'%(n, v))
				
	def prepare_test(self):
		self.copy_cfg_files()
		self.record_case_info()
		self.record_environment()
		
	def end_work(self, workdir, log_file):
		SHELL.call('xcopy /y /q %s\\nn_result_dump_0.txt %s\\' % (workdir, self.result_path))
		SHELL.call('xcopy /y /q %s\\output*.txt %s\\' % (workdir, self.result_path))
		
	def run(self):
		self._info("===start test: %s" % self)
		
		SHELL.call("md %s" % self.result_path)
		if not self.coveraged_case():
			with open(os.path.join(self.result_path, self.key+'.txt'), 'w') as f:
				f.write("Status: NotSupport. Time: 0")
				self._info("Skip: not support.")
				return 0
				
		with self.tester._mutex:
			(workdir, delete) = self.append_workdir()
		self.install_case(workdir)
		self.prepare_test()
		
		log_file = os.path.join(workdir, self.key+'.txt')
		with open(log_file, 'w') as f:
			with self.tester._mutex:
				os.chdir(workdir)
				try:
					self._info("Start to run at %s" % os.getcwd())
					start = datetime.now()	
					child = SHELL.Popen(self.cmdline, stdout=f)
				except:
					import traceback
					self._error("Failed to start: %s" % self.cmdline)
					traceback.print_exc()
					f.write("\nStatus: Cases error. Time: 0")
					SHELL.call('xcopy /y /q %s %s\\' % (log_file, self.result_path))
					return -1
			status = 'Finish'	
			try:	
				ret = child.wait(self._timeout)
			except subprocess.TimeoutExpired:
				status = 'Timeout'
				child.terminate()
				self._error("Timeout (%s)", self._timeout)
			end = datetime.now()
			if ret != 0:
				status = 'Crash'
			f.write("\nStatus: %s. Time: %s" % (status, (end-start).seconds))
		self.end_work(workdir, log_file)
		SHELL.call('xcopy /y /q %s %s\\' % (log_file, self.result_path))
		if delete:
			os.chdir(os.path.dirname(workdir))
			shutil.rmtree(workdir, True)
		self._info("Finish: Status: %s. Time: %s" % (status, (end-start).seconds))
			
class NN_unit_case(NN_case):
	def __init__(self, category, name, group, item):
		super(NN_unit_case, self).__init__(category, name)
		self._group	= group
		self._item	= item
		self._timeout = 24 * 3600
		
	def __str__(self):
		return ' '.join([self._category, self._name, self._group, self._item])
		
	@property
	def key(self):
		return self._item
		
	@property
	def bin(self):
		return self._item
		
	@property
	def cmdline(self):
		return self._item
		
	@property
	def case_path(self):
		return os.path.join(CASE_HOME, self._category, self._name, self._group, self._item)
		
	@property
	def work_path(self):
		return os.path.join(self.tester._workdir, self._category, self._name, self._group, self._item)
		
	def prepare_test(self):
		with self.tester._cfg_mutex:
			if not os.path.exists(os.path.join(self.result_path, "cfg.ini")):
				SHELL.call("xcopy /y/q %s\\*.ini %s\\" % (self.tester._local_driver, self.result_path))
				SHELL.call("xcopy /y/q %s\\case_info.ini %s" % (os.path.join(CASE_HOME, self._category, self._name), self.result_path))
				self.record_environment()
				
	def end_work(self, workdir, log_file):
		pass
				
class Ocl_cts_case(NN_case):
	def __init__(self, category='ocl12', name='cts', bin=None, c_args=''):
		super(Ocl_cts_case, self).__init__(category, name)
		assert bin
		self._bin		= bin
		self._c_args	= c_args
		self._timeout	= 10 * 24 * 3600
		
	def __str__(self):
		return ' '.join([self._category, self._name, self._bin, self._c_args])
		
	@property
	def key(self):
		s = '_'.join([self._bin.replace('conformance_', '').replace('test_', '')] + self._c_args.split())
		return s.replace('*', '')
		
	@property
	def cmdline(self):
		return ' '.join([self._bin, self._c_args])
		
	@property
	def bin(self):
		return self._bin
		
	@property
	def case_path(self):
		return os.path.join(CASE_HOME, self._category, self._name)
		
	@property
	def result_path(self):
		return os.path.join(self.tester._savedir, self._category, self._name, self.key)
		
	@property
	def work_path(self):
		return os.path.join(self.tester._workdir, self._category, self._name, self._bin)
		
	def coveraged_case(self):
		return True
		
	def install_case(self, dst):
		SHELL.call("xcopy /y/q %s\\%s.exe %s\\" % (self.case_path, self._bin, dst))
		SHELL.call("xcopy /y/q/s %s\\* %s\\" % (self.tester._local_driver, dst))
		self._info("Finish install cases")
		
	def record_case_info(self):
		case_info = os.path.join(self.result_path, 'case_info.ini')
		try:
			i_parser = configparser.ConfigParser()
			i_parser.read(case_info)
			if not i_parser.has_section(self._name):
				i_parser.add_section(self._name)
			i_parser.set(self._name, 'category', self._category)
			i_parser.set(self._name, 'bin', self.bin)
			i_parser.set(self._name, 'args', self._c_args)
			i_parser.write(open(case_info, 'w'))
		except:
			pass

	def prepare_test(self):
		SHELL.call("xcopy /y/q %s\\*.ini %s\\" % (self.tester._local_driver, self.result_path))
		SHELL.call("xcopy /y/q %s\\case_info.ini %s\\" % (self.case_path, self.result_path))
		self.record_case_info()
		self.record_environment()
		
	def end_work(self, workdir, log_file):
		pass
				
class Tester(object):
	def __init__(self, **kargs):
		if kargs.get('driver'):
			self._driver	= kargs.get('driver')
			tmp				= self._driver.split(os.sep)
			cmodel_branch	= tmp[-4]
			driver_branch	= tmp[-3]
			version			= tmp[-2]
			self._chip		= tmp[-1]
			self._savedir	= os.path.join(RESULT_HOME, cmodel_branch, driver_branch, version, self._chip)
		else:
			cmodel_branch	= kargs.get("cmodel_branch")
			driver_branch	= kargs.get("driver_branch")
			version			= kargs.get("version")
			self._chip		= kargs.get("chip")
			self._driver	= os.path.join(SDK_HOME, cmodel_branch, driver_branch, version, self._chip)
			self._savedir	= os.path.join(RESULT_HOME, "autotest", cmodel_branch, driver_branch, version, self._chip)
		
		#用以匹配build driver时，有gcDefines_的情况
		if not os.path.exists(self._driver):
			self._driver = os.path.join(SDK_HOME, cmodel_branch, driver_branch, version, 'gcDefines_' + self._chip)
			if not os.path.exists(self._driver):
				raise ValueError("can not find driver: %s" % self._driver)
				
		self._workdir		= os.path.join(os.getcwd(), 'workspace')#组建一个由当前工作目录+workspace构成的字符串
		self._local_driver	= os.path.join(self._workdir, cmodel_branch, driver_branch, version, self._chip)
		self._logger		= logging.getLogger(','.join([cmodel_branch, driver_branch, version, self._chip]))
		
		self._mutex 			= threading.Lock()
		self._cfg_mutex 		= threading.Lock()
	
	def init_test(self):
		SHELL.call("md %s" % self._local_driver)
		SHELL.call("md %s" % self._savedir)
		UT.xcopy(self._driver, self._local_driver)
		SHELL.call("xcopy /y/q %s\\*.ini %s" % (self._driver, self._savedir))
		os.environ['path'] = "%s;%s" % (self._local_driver, os.environ['path'])#往环境变量path里添加本地driver的路径
		tmp = self._chip.split('_')
		os.environ['HW_CONFIG'] = tmp[-1].replace('pid', '')
		os.environ['VIV_VX_ENABLE_PRINT_TARGET'] = str(1)#str(1)将数字1转换成字符串1
		
		with open("\\\\192.168.33.105\\data\\test_envs\\hw_configs\\latest.txt", 'r') as f:
			latest = f.readline().strip()
		env_file = os.path.join("\\\\192.168.33.105\\data\\test_envs\\hw_configs", latest, tmp[-1].replace('pid', '')+'.sh')
		if os.path.exists(env_file):
			with open(env_file, 'r') as f:
				lines = f.readlines()
			for line in lines:
				tmp = line.strip().split()
				keys = tmp[1].split('=')
				os.environ[keys[0]] = keys[1]
		
	def run(self, case):
		case.tester = self
		case.run()
