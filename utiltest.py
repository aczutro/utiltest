#!/usr/bin/python3
'''library for advanced automated testing of command line utilities'''
#
# utiltest - python library for advanced automated testing of command line utilities
#
# Copyright 2017 Alexander Czutro
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this module.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################### aczutro ###

from __future__ import print_function; # for compatibility with Python 2
from subprocess import Popen as _child, PIPE as _pipe;
from os import makedirs as _mkdirs, \
    symlink as _symlink, \
    remove as _rm, \
    rmdir as _rmdir;
from os.path import isdir as _isdir, isfile as _isfile, islink as _islink;

from os.path import exists as _exists, realpath as _realpath;

import aczutro;
aczutro.check_version(1, 0);

version_info = aczutro.VersionInfo(2, 0);
__version__ = str(version_info);
__author__ = 'Alexander Czutro, github@czutro.ch';

def check_version(*version):
    '''Returns True if current version of this module is greater
    or equal to 'version'.  Throws ValueError otherwise.'''
    if version <= version_info:
        return True;
    else:
        raise ValueError("Version %s of module '%s' not available." %
                         ('.'.join([str(i) for i in version]), __name__)
        );
    #else
#check_version


### class for the management of temporal files ################################

class TMPFileManager:
    '''Manager of temporal files.  Should be initialised in a with statement.
    Then, all temporal files/directories/symlinks created via the manager or
    registered with the manager within the with block, are automatically
    deleted at the end of the with block (if they still exist; if they don't,
    no error is raised).'''
    def __enter__(self):
        self.files = [];
        self.own_files = [];
        return self;
    #__enter__


    def __exit__(self, type, value, traceback):
        for f in reversed(self.files):
            if _exists(f):
                if _isdir(f):
                    _rmdir(f);
                else:
                    _rm(f);
                #else
            #if
        #for
    #__exit__


    def add_directory(self, directory):
        '''Creates a temporal directory.'''
        if _exists(directory):
            raise ValueError("file/directory '%s' already exists" % directory);
        #if
        _mkdirs(directory, 0o755);
        self.files.append(directory);
    #add_directory


    def register_directory(self, directory):
        '''Registers an existing directory for deletion
        at the end of the with block.'''
        if not _exists(directory) or not _isdir(directory):
            raise ValueError(
                "directory/file '%s' doesn't exist or is not a directory"
                % directory);
        #if
        self.files.append(directory);
    #register_directory


    def add_file(self, filename, *contents):
        '''Creates a temporal file (empty if 'contents' is (None)).'''
        if _exists(filename):
            raise ValueError("file/directory '%s' already exists" % filename);
        #if
        with open(filename, 'x') as f:
            if contents:
                print(*contents, file=f);
            #if
        #with
        self.files.append(filename);
        self.own_files.append(filename);
    #add_file


    def modify_file(self, filename, *contents):
        '''Modifies the contents of a temporal file.  For security reasons, this
        is only possible with files that have been previously added via
        add_file(...).'''
        if filename not in self.own_files:
            raise ValueError("can't overwrite unmanaged file '%s'" % filename);
        #if
        if not _exists(filename):
            raise ValueError("file '%s' doesn't exist" % filename);
        #if
        with open(filename, 'w') as f:
            if contents:
                print(*contents, file=f);
            #contents
        #with
    #add_file


    def register_file(self, filename):
        '''Registers an existing file for deletion
        at the end of the with block.'''
        if not _exists(filename) or not _isfile(filename):
            raise ValueError(
                "directory/file '%s' doesn't exist or is not a regular file"
                % filename);
        #if
        self.files.append(filename);
    #register_file


    def add_symlink(self, link, target):
        '''Creates a temporal symbolic link to 'target'.'''
        if _exists(link):
            raise ValueError("file/directory '%s' already exists" % link);
        #if
        _symlink(_realpath(target), link);
        self.files.append(link);
    #add_symlink


    def register_symlink(self, link):
        '''Registers an existing symbolic link for deletion
        at the end of the with block.'''
        if not _exists(link) or not _islink(link):
            raise ValueError(
                "directory/file '%s' doesn't exist or is not a symbolic link"
                % link);
        #if
        self.files.append(link);
    #register_symlink


    def unmanage_files(self):
        '''Unmanages previously added files/links/directories, so they won't
        be deleted at the end of the with block.
            This actually defeats the purpose of this class.  Hence, it
        should be used only for debugging purposes.'''
        self.files = [];
    #unmanage_files
#TMPFileManager



### exception class for failed experiments ####################################

class TestExperimentFailure(Exception):
    '''Exception class to hold info on failed test experiments.'''
    def __init__(self, *args):
        Exception.__init__(self, '''Test experiment failed.
Details:
    command line: %s
    stdin:        %r
    return code:
        expected: %s
        returned: %s
    stdout:
        expected: %r
        returned: %r
    stderr:
        expected: %r
        returned: %r
    failed files: %r''' % args
        );
        self.cmd, self.stdin, \
            self.exp_code, self.act_code, \
            self.exp_stdout, self.act_stdout, \
            self.exp_stderr, self.act_stderr, \
            self.failed_files = args;
    #__init__
#TestExperimentFailure

### test bench ################################################################

class TestBench:
    '''A test experiment consists in:
        - running an external application (application-under-test -- AUT)
          and capturing its exit code and the data it writes to STDOUT and
          STDERR,
        - comparing exit code, STDOUT and STDERR buffers to their expected
          values,
        - performing a file check, i.e. checking whether the AUT has created
          the expected files and whether those files have the right
          contents.
        The test experiment is successful if all checks listed above are
    successful.
        This class provides the means to perform any number of test
    experiments with little preparation.  Use the functions that start with
    'set_' or with 'cmd' to specify or manipulate the command line that will
    run the AUT, to set the input to be passed to the AUT, and to register
    the expected values for exit code and output buffers.  Use
    add_file_check(...) to register files for the file check.  Use
    reset(...) to reset one, several or all parameters back to the test
    bench's default state (empty command line, no file check, exit code 0
    and empty ouput buffers).  Finally, use execute() to run the test
    experiment as specified above.  If the test experiment is succesful,
    nothing happens and you can continue to use the test bench for further
    experiments.  If the experiment fails, execute() raises an exception
    with a detailed description of why the experiment failed.
    '''

    CMD, STDIN, CODE, STDOUT, STDERR, FILES = (2**i for i in range(6));
    ALL = 63; # 2**6 - 1


    def __init__(self, verbose=False):
        '''Initialises self.'''
        self.cmd = None;
        self.stdin = None;
        self.code = None;
        self.stdout = None;
        self.stderr = None;
        self.reset(self.ALL);
        self.verbose = verbose;
        self.files = [];
    #__init__


    def __repr__(self):
        '''Returns repr(self).'''
        return '%s : %r : %s : %r : %r : %r' % (
            self.cmd, self.stdin,
            self.code, self.stdout,
            self.stderr, self.files);
    #__repr__


    def set_verbose(self, verbose):
        '''Sets test bench's verbosity.  verbose is a Boolean flag.'''
        self.verbose = verbose;
    #set_verbose


    def pprint(self):
        '''Pretty-prints self.'''
        print('-----------------------------------------------');
        print('\n'.join([' '.join((label, repr(elmt)))
                         for label, elmt in
                         [('command line   :', self.cmd),
                          ('stdin          :', self.stdin),
                          ('expected code  :', self.code),
                          ('expected stdout:', self.stdout),
                          ('expected stderr:', self.stderr),
                          ('files          :', self.files)
                         ]
        ]));
    #pprint


    def reset(self, what):
        '''Resets the fields specified by 'what'.  'what' is ALL or
        the bitwise disjunction of one or several of CMD, STDIN,
        CODE, STDOUT, STDERR and FILES.'''
        if what & self.CMD:
          self.cmd = [];
        #if
        if what & self.STDIN:
          self.stdin = None;
        #if
        if what & self.CODE:
          self.code = 0;
        #if
        if what & self.STDOUT:
          self.stdout = '';
        #if
        if what & self.STDERR:
            self.stderr = '';
        #if
        if what & self.FILES:
            self.files = [];
        #if
    #reset


    def set_cmd(self, *cmd):
        '''Sets command to execute in the experiment.'''
        self.cmd = list(cmd);
    #set_cmd


    def cmd_append(self, *cmd):
        '''Appends the given arguments to command.'''
        self.cmd.extend(cmd);
    #cmd_append


    def cmd_pop(self, index=None):
        '''Removes index'th token from command line,
        or the last if index is None.
        index may also be negative (to address command
        line tokens counting backwards from the end).
        '''
        if index:
            self.cmd.pop(index);
        else:
            self.cmd.pop();
        #else
    #cmd_pop


    def cmd_insert(self, index, newarg):
        '''Inserts newarg into command line at index.
        index may also be negative (to address command
        line tokens counting backwards from the end).
        '''
        self.cmd.insert(index, newarg);
    #cmd_insert


    def cmd_replace(self, index, newarg):
        '''Replaces index'th token of cmd by newarg.
        index may also be negative (to address command
        line tokens counting backwards from the end).
        '''
        self.cmd[index] = newarg;
    #cmd_replace


    def set_stdin(self, value):
        '''Set STDIN to be passed to the tested program.'''
        self.stdin = value.encode('utf-8');
    #set_stdin


    def set_expected(self, arg1, arg2, arg3=None):
        '''If 3 arguments are given (disregarding self):
            - set code to first argument,
            - set stdout to second argument,
            - set stderr to third argument.
            If 2 arguments are given (disregarding self),
        set code, stdout or stderr to second argument.
        First argument specifies which.'''
        if arg3 is None: # arg1 is what and arg2 is value
            if arg1 & self.CODE:
                self.code = arg2;
            elif arg1 & self.STDOUT:
                self.stdout = arg2;
            elif arg1 & self.STDERR:
                self.stderr = arg2;
            else:
                raise ValueError(
                    'arg2 must be TestBench.CODE, TestBench.STDOUT or TestBench.STDERR.'
                );
            #else
        else: # arg1 is code, arg2 is stdout and arg3 is stderr
            self.code = arg1;
            self.stdout = arg2;
            self.stderr = arg3;
        #else
    #set_expected


    EXISTS = True;
    NOT_EXISTS = False;

    def add_file_check(self, filename, mode):
        '''After running the AUT, execute() will also do a file check for each
        file registered with this function.  mode determines the type of the
        file check to be performed:
            - mode == TestBench.EXISTS: check successful if the file exists
            - mode == TestBench.NOT_EXISTS: check successful if the file doesn't
                                            exist
            - mode is a string: check successful is the file exists and its
                                contents are identical to those of mode
        '''
        if mode not in (self.EXISTS, self.NOT_EXISTS) \
           and not isinstance(mode, str):
            raise ValueError('content must be TestBench.EXISTS, '
                             'TestBench.NOT_EXISTS or a string');
        #if
        self.files.append((filename, mode));
    #add_file_check


    def execute(self):
        '''Runs test experiment and raises an Exception with a detailed
        description if the experiment fails.'''
        if self.verbose:
            self.pprint();
        #if
        P = _child(self.cmd, stdin=_pipe, stdout=_pipe, stderr=_pipe);
        stdout, stderr = (data.decode() for data in P.communicate(self.stdin));
        failed_files = self._file_check();
        if (P.returncode != self.code
            or stdout != self.stdout
            or stderr != self.stderr
            or failed_files
        ):
            if self.stdin:
                self.stdin = self.stdin.decode();
            #if
            raise TestExperimentFailure(
                ' '.join((self._fix(token) for token in self.cmd)),
                self.stdin,
                self.code, P.returncode,
                self.stdout, stdout,
                self.stderr, stderr,
                failed_files
            );
        #if
    #execute


    def _fix(self, string):
        '''Private function: Adds appropriate quotes to string for
        printing of final command line.'''
        if string:
            if self._has_one_not_of(
                    string,
                    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_=+~:,./'
            ):
                if string.find("'") != -1:
                    return '"%s"' % string;
                else:
                    return "'%s'" % string;
                #else
            else:
                return string;
            #else
        else:
            return "''";
        #else
    #_fix


    def _has_one_not_of(self, string, chars):
        '''Private function: Returns true if string includes a character
        not contained in chars.'''
        for ch in string:
            if ch not in chars:
                return True;
            #if
        #for
        return False;
    #_has_one_not_of


    def _file_check(self):
        '''Private function: Performs the file check.  If the test passes,
        returns [].  If the test doesn't pass, returns a list of tuples
        (f_i, r_i), where the f_i are files that didn't pass the test and
        the r_i are None if the file doesn't exist, or the file's actual
        contents as a string if it exists.'''
        failed_files = [];
        for filename, mode in self.files:
            if mode == self.NOT_EXISTS:
                if _exists(filename):
                    failed_files.append((filename, 'file exists'));
                #if
            else:
                if not _exists(filename):
                    failed_files.append((filename, "file doesn't exist"));
                elif isinstance(mode, str):
                    with open(filename, 'r') as f:
                        actual_content = f.read();
                        if actual_content != mode:
                            failed_files.append((filename,
                                                 "wrong contents: >>>%s<<<"
                                                 % actual_content));
                        #if
                    #with
                #elif
            #else
        #for
        return failed_files;
    #_file_check
#TestBench


### examples ##################################################################

if __name__ == '__main__':

    # Instantiate a test bench object.  If the argument passed to the
    # constructor is True, the test bench will print information on the
    # experiment each time an experiment is executed.
    TB = TestBench(True);

    # This tests the command line "echo hello world".  It is expected to print
    # the message "hello world" (with a trailing newline) to STDOUT, and to
    # return the exit code 0 (successful).
    TB.set_cmd('echo', 'hello', 'world');
    TB.set_expected(0, 'hello world\n', '');
    TB.execute();

    # This tests the command line "cat" when passed the STDIN message "hello
    # world".  This is equivalent to testing "cat FILE" where FILE is a file
    # containing exactly one line that reads "hello world".
    # The expected output is the same as in the previous experiment, so it
    # doesn't need to be set again.
    TB.set_cmd('cat');
    TB.set_stdin('hello world\n');
    TB.execute();

    # This tests the command line "false" which always returns the exit code 1.
    # There are no inputs or outputs.
    TB.set_cmd('false');
    TB.reset(TB.STDOUT | TB.STDIN | TB.STDERR);
    TB.set_expected(TB.CODE, 1);
    TB.execute();

    # This tests the command line utility "false" again. It is expected to
    # ignore all command line arguments and to exit with code 1.
    TB.cmd_append('ignored', 'arguments', '-and', '--options');
    TB.execute();

    # This tests the command line utility "true" with the same arguments we
    # passed to "false" in the last experiment.  It should exit with code 0.
    # However, we are intentionally not updating the expected return code
    # registered in the test bench in order to show what happens when a test
    # fails.
    TB.set_cmd('true', 'This failure is intentional -- test passed!');
    TB.execute();

    exit(0);
#if

### end ########################################################### aczutro ###
