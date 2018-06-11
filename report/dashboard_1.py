import os, sys
import glob
import xlsxwriter as xw
import config as CFG
import models
import views

def results(path, file_name):
	chip = os.path.basename(path)

	test_env = models.TEST_ENV(os.path.join(path, 'cfg.ini'))
	workbook = xw.Workbook(file_name)
	sum_sheet = workbook.add_worksheet('Summary')

	sum_info = dict()
	for subtest in CFG.TEST.get(chip, CFG.DefaultSubtests):
		sheet = workbook.add_worksheet(subtest)
		sum_info[subtest] = views.print_general_sheet(
					workbook, 
					sheet,
					path=path,	
					test_env=test_env,
					tasks=CFG.get_cases(subtest, chip),#tasks是类似[nn,unit_test_7.1,case_name]形式的列表
					category=CFG.SUBTESTS.get(subtest),
				)

	views.print_summary_sheet(workbook, sum_sheet, test_env=test_env, summary=sum_info)
	workbook.close()

if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser()

	parser.add_argument('path', help='Results saved directory.')
	parser.add_argument('-s', '--save_dir', default=os.getcwd(), help='Diretory to save report')

	args = parser.parse_args()

	assert args.path
	assert os.path.exists(args.path)
	
	version = os.path.basename(args.path)#driver,cmodel,reg,bin,tools的版本号
	temp = (os.path.normpath(args.path)).split(os.sep)
	report = "{c}_{ver}.xlsx".format(temp[-2],temp[-1])
	#results(chip, os.path.join(args.save_dir, report))
	
	for chip in glob.glob(os.path.join(args.path, '*')):
		# report = "{c}_{ver}.xlsx".format(
					# c = os.path.basename(chip).replace('gcDefines_', ''),
					# ver = version
				# )
		results(chip, os.path.join(args.save_dir, report))				
