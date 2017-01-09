#!/usr/bin/env python

# Copyright (C) 2015-2016 Bohdan Khomtchouk and Kasra A. Vand
# This file is part of PubData.

# -------------------------------------------------------------------------------------------

from FTPwalker import main_walker
from os import path, makedirs, listdir
from PyQt4 import QtGui
from PyQt4.QtCore import *
import shutil
import re


class Update(QThread):
    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.exiting = False
        self.server_path = None

    def __del__(self):
        self.exiting = True
        self.wait()

    def render(self, name, url, root='/'):
        print("render")
        name = re.sub(r'\W', '_', name)
        try:
            server_path = path.join(path.dirname(__file__), name)
        except Exception as exc:
            self.emit(SIGNAL("update_message"), 'error', "invalid server name. {}".format(exc))
        else:
            self.server_path = server_path
            self.m_walker = main_walker.main_walker(server_name=name,
                                                    url=url,
                                                    server_path=self.server_path,
                                                    root=root)
            self.start()

    def run(self):
        # Note: This is never called directly. It is called by Qt once the
        # thread environment has been set up.
        # self.emit(SIGNAL("update_message"), 'error', "Sucessfully start updating!")
        try:
            if path.isdir(self.server_path):
                if len(listdir(self.server_path)) > 0:
                    self.path_exit()
                else:
                    self.path_not_exit(False)
            else:
                self.path_not_exit(True)
        except Exception as exc:
            self.emit(SIGNAL("update_message"), 'error', "stoping the update! {}".format(exc))

    def path_exit(self):
        """
        .. py:attribute:: path_exit()

        Runs if If a wanlker kas been run already.

           :rtype: None

        """
        print('path_exit')
        quit_msg = """It seems that you've already
started traversing a server with this name.
Do you want to continue with current one(Y/N)?: """
        while True:
            reply = self.emit(SIGNAL("update_message"), 'question', quit_msg)

            if reply == QtGui.QMessageBox.Yes:
                if self.daemon:
                    daemon_obj.start(self.m_walker.Process_dispatcher, True)
                else:
                    self.m_walker.Process_dispatcher(True)
                return "Start resuming the {} server...".format(self.name)
                # break
            else:
                # deleting the directory
                shutil.rmtree(self.server_path)
                if self.daemon:
                    daemon_obj.start(self.m_walker.Process_dispatcher, False)
                else:
                    self.m_walker.Process_dispatcher(False)
                return "Deleting the directory and start updating the {} server...".format(self.name)
            self.emit(SIGNAL("update_again"))
                # break

    def path_not_exit(self, create_dir):
        """
        .. py:attribute:: path_not_exit()
        Runs if there is no unsuccessful traversed server with this name.

           :param create_dir: A boolean value for creating a directory for this server
           in order to preserving the temp files.
           :type create_dir: boolean
           :rtype: None

        """
        # create the directory
        if create_dir:
            makedirs(self.server_path)
        self.m_walker.Process_dispatcher(False)


def update(server_name, url):
    walker = ftpwalker(server_name, url, daemon=False)
    status = walker.chek_state()
    return status
