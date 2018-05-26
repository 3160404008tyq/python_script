import os, sys
import re, glob
import configparser
from collections import OrderedDict
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utility.sys_call import SHELL

class TEST_ENV(object):
	def __init__(self, cfg=None):
		self.env = OrderedDict()
		self.env['driver'] = None
		self.env['driver_branch'] = None
		self.env['cmodel'] = None
		self.env['cmodel_branch'] = None
		self.env['gcdefine'] = None
		self.env['build_config'] = None
		self.env['reg'] = None
		self.env['tools_bin'] = None
		self.env['rendertarget'] = None

		if cfg is not None and os.path.exists(cfg):
			i_parser = configparser.ConfigParser()
			i_parser.read(cfg)
			self.env['driver_branch'] = i_parser.get('driver', 'branch')
			self.env['driver'] = i_parser.get('driver', 'version')
			branch = i_parser.get('cmodel', 'branch')
			sub_branch = i_parser.get('cmodel', 'sub_branch')
			self.env['cmodel_branch'] = "{b}{s}".format(
					b=branch, 
					s='/%s'%sub_branch if sub_branch != '' else '')
			self.env['cmodel'] = i_parser.get('cmodel', 'version')
			self.env['gcdefine'] = i_parser.get('cmodel', 'gcDefine')
			self.env['reg'] = i_parser.get('reg', 'version')
			self.env['tools_bin'] = i_parser.get('tools', 'version')
			self.env['rendertarget'] = i_parser.get('RenderTarget', 'version')
			self.env['build_config'] = i_parser.get('driver', 'build_cfg')

	@property
	def hierachy(self):
		return self.env.keys()

class RLT_SUM(object):
	
	def __init__(self):
		self.info = OrderedDict()
		self.info['Total'] = 0
		self.info['Pass'] = 0
		self.info['Fail'] = 0
		self.info ['Crash'] = 0
		self.info['Timeout'] = 0
		self.info['NotSupport'] = 0
		self.info['Other'] = 0
	
	@classmethod
	def hierachy(cls):
		return ['Total', 'Pass', 'Fail', 'Crash', 'Timeout', 'NotSupport', 'Other']
		 
class RLT(object):
	def __init__(self, path, name, **kargs):
		self.info = OrderedDict()
		self.info['Name'] = name
		self.info['P4cl'] = None
		self.info['Status'] = 'Miss'
		self.info['Time'] = 0
		cfg = os.path.join(path, 'case_info.ini')
		if os.path.exists(cfg):
			self.info['Status'] = 'Running'
			i_parser = configparser.ConfigParser()
			i_parser.read(cfg)
			self.info['P4cl'] = i_parser.get(os.path.basename(path), 'p4cl')

	def get_status(self, file):
		status, time = 'Running', ''
		with open(file, 'r') as f:
			lines = f.readlines()
		if len(lines) == 0:
			return status, time
		line = lines[-1]

		m = re.match(r'^Status:\s+(?P<status>\w+)\.\s+Time:\s+(?P<time>\w+)$', line)
		if m:
			time = m.group('time')
			status = m.group('status')

		return (status, time)

	@classmethod
	def hierachy(cls):
		return ['Name', 'P4cl', 'Status', 'Time']

class UNIT_RLT_ITEM(RLT):
	def __init__(self, path, name, **kargs):
		super(UNIT_RLT_ITEM, self).__init__(path, name)
		self.info['Operation_target'] = None
		self.info['Layer_name'] = None
		self.info['Operation_type'] = None
		
		log_file = os.path.join(path, name) + '.txt'
		if not os.path.exists(log_file):
			return

		(status, self.info['Time']) = self.get_status(log_file)
		if status != 'Finish':
			self.info['Status'] = status
			return

		with open(log_file, 'r') as f:
			lines = f.readlines()
		
		if len(lines) == 0:
			return	
		index = len(lines) - 1

		m = re.match(r'layer name (.+?)\, operation type (.+?)\, operation target (\w+)', lines[0].strip())
		if m:
			self.info['Layer_name'] = m.group(1)
			self.info['Operation_type'] = m.group(2)
			self.info['Operation_target'] = m.group(3)
			
		while True:
			line = lines[index].strip()
			if re.search(r'Result Pass', line):
				self.info['Status'] = 'Pass'
				break
			if re.search(r'Result Fail', line):
				self.info['Status'] = 'Fail'
				break
			index -= 1
			if index == -1:
				break

	@classmethod
	def hierachy(cls):
		return ['Name', 'P4cl', 'Status', 'Time', 'Operation_target', 'Layer_name', 'Operation_type']

class NN_TOP5_RLT(RLT):
	def __init__(self, path, name, **kargs):
		super(NN_TOP5_RLT, self).__init__(path, name)
		self.info['Result'] = None
		self.info['Golden'] = None
		section = kargs.get('section', 'cmodel')
		if not os.path.exists(path):
			return

		rlog = os.path.join(path, '%s.txt'%name)
		(status, self.info['Time']) = self.get_status(rlog)
		if status != 'Finish':
			self.info['Status'] = status
			return
		
		glog = os.path.join(path, 'golden.txt')
		ret = parse_nn_log_top5(rlog)
		golden = get_nn_top5_golden(glog, section)
		self.info['Result'] = '\n'.join(ret)
		self.info['Golden'] = '\n'.join(golden)
		if len(golden) == 0 and len(ret) != 0:
			self.info['Status'] = 'Golden Miss'
		elif len(ret) == 0:
			self.info['Status'] = 'Miss'
		else:
			if ret == golden:
				self.info['Status'] = 'Pass'
			else:
				self.info['Status'] = 'Fail'
			
	@classmethod
	def hierachy(cls):
		return ['Name', 'P4cl', 'Status', 'Time', 'Result', 'Golden']

class NN_FULL_RLT(RLT):
	def __init__(self, path, name, **kargs):
		super(NN_FULL_RLT, self).__init__(path, name)
		self.info['total'] = None
		self.info['total_same'] = None
		self.info['total_acceptable_diff'] = None
		self.info['total_veto_diff'] = None
		self.info['same_ratio'] = None

		log_file = os.path.join(path, name+'.txt')
		if not os.path.exists(log_file):
			return
		(status, self.info['Time']) = self.get_status(log_file)
		if status != 'Finish':
			self.info['Status'] = status
			return

		chip = kargs.get('chip', 'unified')	
		if not os.path.exists(path):
			return
		script = os.path.join(path, 'check_result.py')
		if not os.path.exists(script):
			return
		rlog = os.path.join(path, 'nn_result_dump_0.txt')
		if not os.path.exists(rlog):
			tmp = glob.glob(os.path.join(path, 'output*.txt'))
			if tmp:
				rlog = tmp[0]
		print(rlog)
		if not os.path.exists(rlog):
			return
		sqa = os.path.join(path, 'sqa.ini')
		if not os.path.join(sqa):
			return
		golden = os.path.join(path, 'golden', chip)
		if not os.path.exists(golden):
			golden = os.path.join(path, 'golden', 'cmodel')
		if not os.path.exists(golden):
			golden = os.path.join(path, 'golden', 'unified')
		glog = os.path.join(golden, 'nn_result_dump.txt')
		if not os.path.exists(glog):
			tmp = glob.glob(os.path.join(golden, 'output*'))
			if tmp:
				glog = tmp[0]
		if not os.path.exists(glog):
			self.info['Status'] = 'Golden Miss'
			return
			
		print('check full result: %s' % name)
		try:
			if path.find('full_network_coverage_1.0') != -1:
				SHELL.call('python %s %s %s --sqa-ini %s --%s --save-dir %s' % (script, rlog, glog, sqa, name_to_dtype(name), path))
			else:
				SHELL.call('python %s %s %s --sqa-ini %s --save-dir %s' % (script, rlog, glog, sqa, path))
		except:
			self.info['Status'] = 'Result check fail'
			return
			
		rlt_file = os.path.join(path, 'compared_result.txt')
		if not os.path.exists(rlt_file):
			self.info['Status'] = 'Result check fail'
			return
			
		f = open(rlt_file, 'r')
		lines = f.readlines()
		f.close()
		
		for line in lines:
			keys = line.split(':')
			if len(keys) == 2:
				if keys[0].strip() == 'result':
					self.info['Status'] = keys[1].strip()
					continue
				self.info[keys[0].strip()] = keys[1].strip()	
	
	@classmethod
	def hierachy(cls):
		return ['Name', 'P4cl', 'Status', 'Time', 'total', 'total_same', 'total_acceptable_diff', 'total_veto_diff', 'same_ratio']

def name_to_dtype(name):
	if name.endswith('_uint8'):
		return 'uint8'
	if name.endswith('_int8'):
		return 'int8'
	if name.endswith('_int16'):
		return 'int16'
		
	return 'fp16'

def parse_nn_log_top5(log_file):
	ret = list()
	if not os.path.exists(log_file):
		return ret

	f = open(log_file, 'r')
	lines = f.readlines()
	f.close()
	
	for line in lines:
		m = re.match(r'\s*\d+:\s*\d', line.strip())
		if m:
			l = line.split(':')
			if float(l[1].strip()) != 0:
				ret.append(line.strip())

	return ret
	
def get_nn_top5_golden(g_file, section='cmodel'):
	ret = list()
	try:
		cfg = configparser.ConfigParser()
		cfg.read(g_file)
		while not cfg.has_section(section):
			keys = section.split(',')
			if len(keys) == 1:
				break
			section = ','.join(keys[0:-1])
		top5 = cfg.get(section, 'top5')
	except:
		return ret
		
	tops = top5.strip('[').strip(']').split(',')
	
	for i in tops:
		v = i.replace('\'', '').strip()
		if float(v.split(':')[1].strip()) != 0:
			ret.append(v)

	return ret
