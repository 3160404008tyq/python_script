
SDK_HOME		= "A:\\cmodel_driver\\autobuilds"
CASE_HOME		= "A:\\cases"
RESULT_HOME		= "A:\\results"
SDK_VERSIONS	= 30

IGNORES = [
	'panasonic_googlenet_int8_005',
	'panasonic_googlenet_int8_007',
	'lstm_asym_uint8',
	'lstm_dfp_int16',
	'lstm_dfp_int8',
	'lstm_fp16',
]

CHIP_IGNORES = {
	'vip8012n8_0003_pid0x7d': IGNORES + [
		'alexnet_int8_010',
		'alexnet_int8_011',
	],
	'vip8012n2_0002_pid0x80': IGNORES + [
		'alexnet_int8_010',
		'alexnet_int8_011',
	],
}