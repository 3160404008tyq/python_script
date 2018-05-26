import subprocess as SP

class SHELL():

	def __init__(self):
		pass

	@classmethod
	def check_call(cls, cmdline):
		return SP.check_call(cmdline, shell=True, stderr=SP.STDOUT)

	@classmethod
	def check_output(cls, cmdline):
		return SP.check_output(cmdline, shell=True, stderr=SP.STDOUT)
		
	@classmethod
	def call(cls, cmdline):
		return SP.call(cmdline, shell=True, stderr=SP.STDOUT)
		
	@classmethod
	def Popen(cls, cmdline, stdout):
		return SP.Popen(cmdline, stdout=stdout)