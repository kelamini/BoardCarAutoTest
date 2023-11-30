import argparse
import codecs
import logging
import os
import os.path as osp
import sys
import yaml

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import QtGui

from boardcardautotest import __appname__
from boardcardautotest import __version__
from boardcardautotest.app import MainWindow

here = osp.dirname(osp.abspath(__file__))

def newIcon(icon):
    icons_dir = osp.join(here, "./icons")
    return QtGui.QIcon(osp.join(":/", icons_dir, "%s.png" % icon))


def main():

    translator = QtCore.QTranslator()
    translator.load(
        QtCore.QLocale.system().name(),
        osp.dirname(osp.abspath(__file__)) + "/translate",
    )
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(__appname__) # 应用名称
    app.setWindowIcon(newIcon("icon"))  # Icon
    app.installTranslator(translator)   # 语言转换

    win = MainWindow()
    win.show()
    win.raise_()
    sys.exit(app.exec_())


# this main block is required to generate executable by pyinstaller
if __name__ == "__main__":
    main()
