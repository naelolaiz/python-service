#!/usr/bin/python

from GitSandbox import GitSandbox
import utils
import os
import unittest

class GitSandboxTest(unittest.TestCase) :
	def s(self, command) :
		return self.x("cd %(sandbox)s && " + command)
	def x(self, command) :
		return utils.run(command%self.defs)
	def inSandbox(self, file) :
		return os.path.join(self.defs['sandbox'],file)
	def addFile(self, file, commit=True) :
		self.s('touch %s'%file)
		self.s('git add %s'%file)
		if commit :
			self.commitFile(file, "added %s" % file)
	def removeFile(self, file, commit=True) :
		self.s('git rm %s'%file)
		if commit :
			self.commitFile(file, "removed %s" % file)
	def addRevisions(self, file, n, commit=True) :
		for i in xrange(n) :
			self.s('echo Change %s >> %s'%(i,file))
			if commit :
				self.commitFile(file,"change %i of %s"%(i,file))
	def pushRevision(self) :
		self.revisions.append(file("%(sandbox)s/.git/refs/heads/master"%self.defs).read().strip())

	def commitFile(self, file, message) :
		self.s('git commit %s -m"%s"'%(file,message))
		self.s('git push origin master')
		self.pushRevision()

	def commitAll(self, message) :
		self.s('git commit -a -m"%s"'%(message))
		self.s('git push origin master')
		self.pushRevision()

	def rewind(self, revisions=1) :
		self.s('git reset --hard HEAD~%i' % revisions)

	def setUp(self) :
		self.defs = dict(
			username = "myuser",
			testdir = os.path.join(os.getcwd(),'testdir'),
			repo    = os.path.join(os.getcwd(),'testdir/repo'),
			#sandbox = os.path.join(os.getcwd(),'testdir/sandbox1'),
			sandbox = '/tmp/testdir/sandbox1',
			)
		self.x('rm -rf %(testdir)s')
		self.x('rm -rf /tmp/testdir')
		self.x('mkdir -p %(testdir)s')
		self.revisions = []
		self.x('git init --bare %(repo)s')
		# TODO: User name
		self.x('git clone %(repo)s %(sandbox)s')
		self.s('touch initialfile')
		self.s('git add initialfile')
		self.commitAll('added initialfile')
		self.s('git push origin master')

	def tearDown(self) :
		""" """
#		self.s('git log ')
		self.x('rm -rf %(testdir)s')
		self.x('rm -rf /tmp/testdir')

	def test_init(self) :
		pass

	def test_state(self) :
		self.addFile('file')
		self.addRevisions('file',3)
		s = GitSandbox(self.defs['sandbox'])
		self.assertEquals(self.revisions[4], s.state())
		self.rewind(3)
		self.assertEquals(self.revisions[1], s.state())

	def test_pendingCommits(self) :
		self.addFile('file')
		self.addRevisions('file',3)
		self.rewind(3)
		s = GitSandbox(self.defs['sandbox'])
		self.assertEquals(
			self.revisions[-3:], s.pendingUpdates())

	def _test_guilty(self) :
		self.addFile('file')
		self.addRevisions('file',3)
		self.x('svn up -r1 %(sandbox)s') # go to r1
		s = GitSandbox(self.defs['sandbox'])
		self.assertEquals(
			[
				('2','myuser',"change 0 of file"),
				('3','myuser',"change 1 of file"),
				('4','myuser',"change 2 of file"),
			], s.guilty())

	def _test_pendingChanges(self) :
		self.addFile('remoteChange', False)
		self.addFile('remoteRemove', False)
		self.addFile('localRemove', False)
		self.addFile('localChange', False)
		self.addFile('nonsvnRemove', False)
		self.commitAll("State were we want to go back")

		self.addRevisions('remoteChange',1, False)
		self.addFile('remoteAdd', False)
		self.removeFile('remoteRemove', False)
		self.commitAll("State we want to update to")
		self.x('svn up -r1 %(sandbox)s') # going back

		# local modifications
		self.addRevisions('localChange', 1, False)
		self.removeFile('localRemove', False)
		self.addFile('localAdd', False)
		self.x('echo nonsvnAdd > %(sandbox)s/nonsvnAdd')
		self.x('rm %(sandbox)s/nonsvnRemove')

		s = GitSandbox(self.defs['sandbox'])
		self.maxDiff = None
		self.assertEquals(
			[
				(self.defs['sandbox'],           ('normal', 'none', 'modified', 'none')),
				(self.inSandbox('localAdd'),     ('added', 'none', 'none', 'none')),
				(self.inSandbox('localChange'),  ('modified', 'none', 'none', 'none')),
				(self.inSandbox('localRemove'),  ('deleted', 'none', 'none', 'none')),
				(self.inSandbox('nonsvnAdd'),    ('unversioned', 'none', 'none', 'none')),
				(self.inSandbox('nonsvnRemove'), ('missing', 'none', 'none', 'none')),
				(self.inSandbox('remoteAdd'),    ('none', 'none', 'added', 'none')),
				(self.inSandbox('remoteChange'), ('normal', 'none', 'modified', 'none')),
				(self.inSandbox('remoteRemove'), ('normal', 'none', 'deleted', 'none')),

			], sorted(s._pendingChanges()))

	def _test_hasPendingChanges_whenNoPendingChanges(self) :
		self.addFile('remoteChange', False)
		self.addFile('remoteRemove', False)
		self.addFile('localRemove', False)
		self.addFile('localChange', False)
		self.addFile('nonsvnRemove', False)
		self.commitAll("State were we want to go back")

		s = GitSandbox(self.defs['sandbox'])
		self.assertFalse(s.hasPendingChanges())

	def _test_hasPendingChanges_whenMissingFile(self) :
		self.addFile('nonsvnRemove')
		self.x('rm %(sandbox)s/nonsvnRemove')

		s = GitSandbox(self.defs['sandbox'])
		self.assertTrue(s.hasPendingChanges())

	def _test_hasPendingChanges_whenPendingModification(self) :
		self.addFile('remoteChange')
		self.addRevisions('remoteChange',1)
		self.x('svn up -r1 %(sandbox)s') # going back

		s = GitSandbox(self.defs['sandbox'])
		self.assertTrue(s.hasPendingChanges())

	def _test_hasPendingChanges_whenPendingRemove(self) :
		self.addFile('remoteRemove')
		self.removeFile('remoteRemove')
		self.x('svn up -r1 %(sandbox)s') # going back

		s = GitSandbox(self.defs['sandbox'])
		self.assertTrue(s.hasPendingChanges())

	def _test_hasPendingChanges_whenPendingAdd(self) :
		self.addFile('remoteAdd')
		self.x('svn up -r0 %(sandbox)s') # going back

		s = GitSandbox(self.defs['sandbox'])
		self.assertTrue(s.hasPendingChanges())

	def _test_hasPendingChanges_whenLocalChanges(self) :
		self.addFile('localRemove', False)
		self.addFile('localChange', False)
		self.commitAll("State were we want to go back")

		# any local modifications (but non-svn deletion)
		self.addRevisions('localChange', 1, False)
		self.removeFile('localRemove', False)
		self.addFile('localAdd', False)
		self.x('echo nonsvnAdd > %(sandbox)s/nonsvnAdd')

		s = GitSandbox(self.defs['sandbox'])
		self.maxDiff = None
		self.assertFalse(s.hasPendingChanges())


if __name__ == '__main__' :
	unittest.main()


