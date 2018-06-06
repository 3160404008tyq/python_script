import os

SUBTESTS = {
	'Unit_test_1.0': 'nn,unit_test_1.0',
	'Neural_Network_full_1.0': 'full_network_coverage_1.0',
	'INT8_Neural_Network_full_1.0': 'full_network_coverage_1.0',
	'INT8_Unit_test_1.0': 'nn,unit_test_1.0',
	'INT16_Unit_test': 'nn,unit_test',
	'SW_Tiling_Unit_test': 'nn,unit_test',
	'TP_tf_INT8_Unit_test': 'nn,unit_test',
	'INT8_Neural_Network': 'nn',
	'INT16_Neural_Network': 'nn',
	'Unit_test_7.1': 'nn,unit_test_7.1',
	'full_network_coverage_7.1': 'full_network_coverage_7.1',
	'Unit_test_7.1_Int': 'nn,unit_test_7.1',
	'full_network_coverage_7.1_Int': 'full_network_coverage_7.1',
}

VIPNanoQiSubtests = [
	'INT8_Unit_test_1.0',
	'INT16_Unit_test',
	'SW_Tiling_Unit_test',
	'TP_tf_INT8_Unit_test',
	'INT8_Neural_Network',
	'INT16_Neural_Network',
	'INT8_Neural_Network_full_1.0',
]

DefaultSubtests = [
	'Unit_test_7.1',
	'full_network_coverage_7.1',
]

TEST = {
	'vip8012n8_0003_pid0x7d': VIPNanoQiSubtests,
}

IGNORES = [
	'nn,unit_test_1.0,panasonic_googlenet_int8_005',
	'nn,unit_test_1.0,panasonic_googlenet_int8_007',
]

CHIP_IGNORES = {
	'vip8012n8_0003_pid0x7d': IGNORES + [
		'nn,unit_test_1.0,alexnet_int8_010',
		'nn,unit_test_1.0,alexnet_int8_011',
	],
	'vip8012n2_0002_pid0x80': IGNORES + [
		'nn,unit_test_1.0,alexnet_int8_010',
		'nn,unit_test_1.0,alexnet_int8_011',
	],
}

def get_cases(name, chip):
	task = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks', '%s.txt'%name)
	assert os.path.exists(task)
	f = open(task, 'r')
	lines = f.readlines()
	f.close()

	tasks = []
	flag = True
	for line in lines:
		line = line.strip()
		if line == '':
			continue
		if line.startswith('#'):
			continue
		task = ','.join([SUBTESTS.get(name), line])
		if task in CHIP_IGNORES.get(chip, IGNORES):
			flag = False
		tasks.append([flag, task])
	return tasks
