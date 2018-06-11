from xlsxwriter.utility import xl_range, xl_rowcol_to_cell
from copy import deepcopy
import collections
from models import *

def RGB(r, g, b):
	return "#{r}{g}{b}".format(
		r	= hex(r).replace('0x', '').upper().zfill(2),
		g	= hex(g).replace('0x', '').upper().zfill(2),
		b	= hex(b).replace('0x', '').upper().zfill(2)
	)

gen_fmt = {
			'align':		'left',
			'valign':		'top',
			'border':		1,
			'text_wrap':	True,
		}

head_tag_fmt = {
			'align':		'center',
			'border':		1,
			'bg_color':		RGB(23,55,93),
			'bold':			True,
			'font_size':	12,
			'font_color':	'white',
		}

head_item_fmt = deepcopy(gen_fmt)
head_item_fmt['bg_color'] = RGB(197, 217, 241)
rlt_pass_fmt = deepcopy(gen_fmt)
rlt_pass_fmt['bg_color'] = RGB(146, 208, 80)
rlt_warn_fmt = deepcopy(gen_fmt)
rlt_warn_fmt['bg_color'] = RGB(255, 255, 0)
rlt_fail_fmt = deepcopy(gen_fmt)
rlt_fail_fmt['bg_color'] = RGB(242, 221, 220)
rlt_note_fmt = deepcopy(gen_fmt)
rlt_note_fmt['bg_color'] = RGB(240, 190, 10)
rlt_notsupport_fmt = deepcopy(gen_fmt)
rlt_notsupport_fmt['bg_color'] = RGB(128, 128, 128)
rlt_notsupport_fmt['font_color'] = 'white'

def get_format(wb, fmt):
	return wb.add_format(fmt)

fmts = dict()

def get_rlt_fmt(status, item):
	fmt = fmts['com']
	if item not in ['Status', 'Result', 'Golden', 'Pass', 'Fail', 'Crash',
   	'Running', 'Other', 'Miss', 'Golden Miss', 'Running', 'Timeout', 'NotSupport']:
		return fmt
	
	if isinstance(status, int) and status != 0:
		fmt = fmts.get(item, fmt)
	if not isinstance(status, int):
		fmt = fmts.get(status, fmts['Other'])
	return fmt

class TABLE(object):
	def __init__(self, category):
		if category == 'nn':
			self.rlt = NN_TOP5_RLT
		elif category.startswith('nn,unit_test'):
			self.rlt = UNIT_RLT_ITEM
		elif category.startswith('full_network_coverage'):
			self.rlt = NN_FULL_RLT
		else:
			self.rlt = RLT

	@property
	def items(self):
		return self.rlt.hierachy()

def get_rlt_name_dir(path, task):
	keys = task.split(',')
	assert len(keys) in [2, 3]

	rlt_path = os.path.join(path, keys[0], keys[1])
	if len(keys) == 2:
		name = os.path.basename(rlt_path)
	else:
		name = keys[2]

	return [rlt_path, name]

def print_head_env(wb, sheet, env, **kargs):#显示测试的环境变量
	"""
		print test environment information
		paramters:
			env: test driver and cmodel information
			start_row: the first row index to write
			start_col: the first column index to write
	"""
	
	row = kargs.get('start_row', 1)
	col = kargs.get('start_col', 0)

	rg = xl_range(row, col, row, col+1)
	sheet.merge_range(rg, 'Test Environment', fmts.get('head_tag'))
	row += 1

	for key in env.hierachy if key != gcdefine else:
		sheet.write(row, col, key, fmts.get('head_item'))
		sheet.write(row, col+1, env.env.get(key, ''), fmts.get('com'))
		row += 1

def print_sum(wb, sheet, **kargs):
	row = kargs.get('start_row', 13)
	col = kargs.get('start_col', 0)

	info = kargs.get('info', None)
	if info is None:
		return

	i = 0
	for item in info.keys():
		sheet.write(row, col+i, item, get_format(wb, head_tag_fmt))
		sheet.write(row+1, col+i, info.get(item, 0), get_rlt_fmt(info.get(item, 0), item))
		i += 1

def print_detail_table(wb, sheet, **kargs):
	"""
	parameters:
		tasks:
		path:
		category:
		chip:
	return:
		result summary
	"""

	rlt_sum = RLT_SUM()

	tasks = kargs.get('tasks', [])
	if len(tasks) == 0:
		return rlt_sum

	category = kargs.get('category', None)
	assert category

	table = TABLE(category)#根据category，选择result比较模板
	row = kargs.get('start_row', 16)
	col = kargs.get('start_col', 0)

	sheet.freeze_panes(row+1, 0)#freeze_panes--冻结窗口
	sheet.set_column(col+1, col+len(table.items)-1, 20)
	i = 0
	for item in table.items:
		sheet.write(row, col+i, item, fmts.get('head_tag'))
		i += 1
	sheet.autofilter(row, col, row, col+len(table.items)-1)
	row += 1

	path = kargs.get('path', None)
	assert path
	assert os.path.exists(path)

	rlt_sum.info['Total'] = len(tasks)
	for [flag, task] in tasks:
		[rlt_path, name] = get_rlt_name_dir(path, task)
		print(name)
		ret = table.rlt(rlt_path, name, chip=kargs.get('chip'), section=','.join(['cmodel', kargs.get('chip')]))
		sts = ret.info.get('Status', 'Miss')
		if flag == False:
			ret.info['Status'] = 'NotSupport'

		i = 0
		for item in table.items:
			sheet.write(row, col+i, ret.info.get(item, ''), get_rlt_fmt(ret.info['Status'], item))
			i += 1

		sts = ret.info['Status']
		if sts not in ['Pass', 'Fail', 'Crash', 'Timeout', 'NotSupport']:
			sts = 'Other'
		rlt_sum.info[sts] += 1
		row += 1

	return rlt_sum

def print_general_sheet(wb, sheet, **kargs):
	"""
		print general result sheet
		parameters:
			test_env: test driver and cmodel information
			tasks: tasks need to check
			category: task type
			start_row: the first row index to write
			start_col: the first column index to write
	"""

	fmts['Pass'] = get_format(wb, rlt_pass_fmt)
	fmts['Fail'] = get_format(wb, rlt_fail_fmt)
	fmts['Crash'] = get_format(wb, rlt_warn_fmt)
	fmts['Timeout'] = get_format(wb, rlt_warn_fmt)
	fmts['Other'] = get_format(wb, rlt_note_fmt)
	fmts['NotSupport'] = get_format(wb, rlt_notsupport_fmt)
	fmts['com']	= get_format(wb, gen_fmt)
	fmts['head_tag'] = get_format(wb, head_tag_fmt)
	fmts['head_item'] = get_format(wb, head_item_fmt)

	test_env = kargs.get('test_env', None)
	assert test_env

	start_row = kargs.get('start_row', 0)
	start_col = kargs.get('start_col', 0)

	sheet.set_column(start_col, start_col, 30)#设置行宽
	sheet.write_url(start_row, start_col, url='internal:Summary!%s'%xl_rowcol_to_cell(start_row, start_col), string='Summary')

	env_row = start_row + 1
	env_col = start_col
	print_head_env(wb, sheet, env=test_env, start_row=env_row, start_col=env_col)

	sum_row = env_row + len(test_env.hierachy) + 2
	sum_col = start_col

	d_row = sum_row + 3
	d_col = start_col

	ret_sum = print_detail_table(
				wb, 
				sheet, 
				start_row=d_row, 
				start_col=d_col,
				path=kargs.get('path'),
				tasks=kargs.get('tasks'), 
				category=kargs.get('category'), 
				chip=test_env.env.get('gcdefine', '')
			)

	print_sum(wb, sheet, start_row=sum_row, start_col=sum_col, info=ret_sum.info)
	
	return ret_sum

def print_summary_sheet(wb, sheet, **kargs):
	"""
		print summary sheet
		parameters:
			test_env: test driver and cmodel information
			summary: subtest summary inforation
	"""
	
	items = ['Category', 'Total', 'Pass', 'Fail', 'Crash', 'Timeout', 'NotSupport', 'Other']

	test_env = kargs.get('test_env', None)
	assert test_env
	
	row = kargs.get('start_row', 1)
	col = kargs.get('start_col', 0)

	sheet.set_column(col, col, 30)
	sheet.set_column(col+1, col+len(items)-1, 20)

	print_head_env(wb, sheet, env=test_env, start_row=row, start_col=col)

	row = row + len(test_env.hierachy) + 2

	i = 0
	for item in items:
		sheet.write(row, col+i, item, fmts['head_tag'])
		i += 1
	row += 1
	
	summary = kargs.get('summary', None)
	assert summary
	for (subtest, rlt) in summary.items():
		sheet.write_url(row, col, url='internal:%s!A1'%subtest, cell_format=fmts['com'], string=subtest)
		for i in range(1, len(items)):
			num = rlt.info.get(items[i], 0)
			sheet.write(row, col+i, num, get_rlt_fmt(num, items[i]))
		row += 1
