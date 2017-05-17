#!/usr/bin/python3
#
# utiltest - python library for the test of command line utilities
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

from __future__ import print_function;
from sys import exit;
from subprocess import Popen as popen, PIPE;


### base class ################################################################

class TestBench:
    '''Base class for test experiments.'''

    CMD, STDIN, CODE, STDOUT, STDERR = (2**i for i in range(5));
    ALL = 31; # 2**5 - 1


    def __init__(self, verbose=False):
        '''Initialises self.'''
        self.cmd = None;
        self.stdin = None;
        self.code = None;
        self.stdout = None;
        self.stderr = None;
        self.reset(self.ALL);
        self.verbose = verbose;
    #__init__


    def __repr__(self):
        '''Returns repr(self).'''
        return '%s : %r : %s : %r : %r' % (
            self.cmd, self.stdin, self.code, self.stdout, self.stderr);
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
                          ('expected stderr:', self.stderr)
                         ]
        ]));
    #pprint


    def reset(self, what):
        '''Resets the fields specified by 'what'.  'what' is ALL or
        the bitwise disjunction of one or several of CMD, STDIN,
        CODE, STDOUT and STDERR.'''
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
    #reset


    def set_cmd(self, *cmd):
        '''Sets command to execute in the experiment.'''
        self.cmd = list(cmd);
    #set_cmd


    def append_to_cmd(self, *cmd):
        '''Appends the given arguments to command.'''
        self.cmd.extend(cmd);
    #append_to_cmd


    def pop_from_cmd(self, index=None):
        '''Removes index'th token from command line,
        or the last if index is None.
        index may also be negative (to address command
        line tokens counting backwards from the end).
        Raises IndexError.
        '''
        if index:
            self.cmd.pop(index);
        else:
            self.cmd.pop();
        #else
    #pop_from_cmd


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
        Raises IndexError.'''
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
        If 2 arguments are given (disregarding self), set
        code, stdout ot stderr to second argument.
        First argument specifies which.'''
        if arg3 is None: # arg1 is what and arg2 is value
            if arg1 & self.CODE:
                self.code = arg2;
            elif arg1 & self.STDOUT:
                self.stdout = arg2;
            elif arg1 & self.STDERR:
                self.stderr = arg2;
            else:
                raise Exception('If fourth positional argument is None,',
                                'second argument must be TestBench.CODE,',
                                'TestBench.STDOUT or TestBench.STDERR.'
                );
            #else
        else: # arg1 is code, arg2 is stdout and arg3 is stderr
            self.code = arg1;
            self.stdout = arg2;
            self.stderr = arg3;
        #else
    #set_expected


    def execute(self):
        '''Runs test experiment and raises an Exception with a detailed
        description if the experiment fails.'''
        if self.verbose:
            self.pprint();
        #if
        P = popen(self.cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE);
        stdout, stderr = (data.decode() for data in P.communicate(self.stdin));
        if (P.returncode != self.code
            or stdout != self.stdout
            or stderr != self.stderr
        ):
            if self.stdin:
                self.stdin = self.stdin.decode();
            #if
            raise Exception('''Test experiment failed.
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
        returned: %r''' % (' '.join((self._fix(token) for token in self.cmd)),
                           self.stdin,
                           self.code, P.returncode,
                           self.stdout, stdout,
                           self.stderr, stderr)
            );
        #if
    #execute


    def _fix(self, string):
        '''Adds appropriate quotes to string for
        printing of final command line.'''
        if string:
            if self._has_one_not_of(
                    string,
                    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_=+~:,.'
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
    #def


    def _has_one_not_of(self, string, chars):
        '''Returns true if string includes a character
        not contained in chars.'''
        for ch in string:
            if ch not in chars:
                return True;
            #if
        #for
        return False;
    #_has_one_not_of
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
    TB.append_to_cmd('ignored', 'arguments', '-and', '--options');
    TB.execute();

    # This tests the command line utility "true" with the same arguments we
    # passed to "false" in the last experiment.  It should exit with code 0.
    # However, we are intentionally not updating the expected return code
    # registered in the test bench in order to show what happens when a test
    # fails.
    TB.cmd_replace(0, 'true');
    TB.execute();

    exit(0);
#if

### end ########################################################### aczutro ###
