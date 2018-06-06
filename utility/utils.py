
import os, sys
import hashlib
import pickle
import shutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sys_call import SHELL

def md5check(fname):
	m = hashlib.md5()
	with open(fname, 'rb') as f:
		while True:
			data = f.read(4096)
			if not data:
				break
			m.update(data)
	return m.hexdigest()

def generate_md5file(src):
	md5 = {}
	for path, folders, files in os.walk(src):
		for fname in files:
			fullpath = os.path.join(path, fname)
			md5[fullpath.replace(src, '')] = md5check(fullpath)

	file = os.path.join(src, 'md5.data')
	with open(file, 'wb') as f:
		pickle.dump(md5, f)

def xcopy(src, dst):
	 SHELL.call('xcopy /y/d/q/e/i %s %s\\'%(src, dst))

def is_same_modify(f1, f2):
	return os.path.getmtime(f1) == os.path.getmtime(f2)

def incr_copy(src, dst):
	md5new = {}

	src_md5file = os.path.join(src, 'md5.data')
	if not os.path.exists(src_md5file):
		return xcopy(src, dst)

	dst_md5file = os.path.join(dst, 'md5.data')

	md5dst = {}

	if os.path.exists(dst_md5file):
		if is_same_modify(src_md5file, dst_md5file):
			return
		with open(dst_md5file, 'rb') as f:
			md5dst = pickle.load(f)	
	if not os.path.exists(dst):
		os.makedirs(dst, exist_ok=True)

	with open(src_md5file, 'rb') as f:
		md5src = pickle.load(f)

	for key in md5src:
		if md5dst.get(key, None) != md5src[key]:
			srcfile = src + key
			dstfile = dst + key
			dstpath = os.path.dirname(dstfile)
			if not os.path.exists(dstpath):
				os.makedirs(dstpath, exist_ok=True)
			shutil.copy2(srcfile, dstfile)

	shutil.copy2(src_md5file, dst_md5file)
