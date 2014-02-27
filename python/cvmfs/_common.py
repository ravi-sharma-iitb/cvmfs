#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created by René Meusel
This file is part of the CernVM File System auxiliary tools.
"""

import ctypes
import tempfile
import zlib
import sqlite3
import subprocess


_REPO_CONFIG_PATH      = "/etc/cvmfs/repositories.d"
_SERVER_CONFIG_NAME    = "server.conf"

_REST_CONNECTOR        = "control"

_MANIFEST_NAME         = ".cvmfspublished"
_LAST_REPLICATION_NAME = ".cvmfs_last_snapshot"
_REPLICATING_NAME      = ".cvmfs_is_snapshotting"


class CvmfsNotInstalled(Exception):
    def __init__(self):
        Exception.__init__(self, "It seems that cvmfs is not installed on this machine!")


class CompressedObject:
    file_ = None

    def __init__(self, compressed_file):
        self._decompress(compressed_file)

    def __del__(self):
        if self.file_:
            self.file_.close()

    def _decompress(self, compressed_file):
        """ Unzip a file to a temporary referenced by self.file_ """
        self.file_ = tempfile.NamedTemporaryFile('w+b')
        self.file_.write(zlib.decompress(compressed_file.read()))
        self.file_.flush()


class DatabaseObject(CompressedObject):
    db_handle_ = None

    def __init__(self, compressed_db_file):
        CompressedObject.__init__(self, compressed_db_file)
        self._open_database()

    def __del__(self):
        if self.db_handle_:
            self.db_handle_.close()

    def _open_database(self):
        """ Create and configure a database handle to the Catalog """
        self.db_handle_ = sqlite3.connect(self.file_.name)
        self.db_handle_.text_factory = str


    def read_properties_table(self, reader):
        """ Retrieve all properties stored in the 'properties' table """
        props = self.run_sql("SELECT key, value FROM properties;")
        for prop in props:
            prop_key   = prop[0]
            prop_value = prop[1]
            reader(prop_key, prop_value)

    def run_sql(self, sql):
        """ Run an arbitrary SQL query on the catalog database """
        cursor = self.db_handle_.cursor()
        cursor.execute(sql)
        return cursor.fetchall()

    def open_interactive(self):
        """ Spawns a sqlite shell for interactive catalog database inspection """
        subprocess.call(['sqlite3', self.file_.name])


def _split_md5(md5digest):
    hi = lo = 0
    for i in range(0, 8):
        lo = lo | (ord(md5digest[i]) << (i * 8))
    for i in range(8,16):
        hi = hi | (ord(md5digest[i]) << ((i - 8) * 8))
    return ctypes.c_int64(lo).value, ctypes.c_int64(hi).value  # signed int!

def _combine_md5(lo, hi):
    md5digest = [ '\x00','\x00','\x00','\x00','\x00','\x00','\x00','\x00',
                  '\x00','\x00','\x00','\x00','\x00','\x00','\x00','\x00' ]
    for i in range(0, 8):
        md5digest[i] = chr(lo & 0xFF)
        lo = lo >> 8
    for i in range(8,16):
        md5digest[i] = chr(hi & 0xFF)
        hi = hi >> 8
    return ''.join(md5digest)