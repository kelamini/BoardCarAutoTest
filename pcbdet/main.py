import argparse
import codecs
import logging
import os
import os.path as osp
import sys
import yaml

from qtpy import QtCore
from qtpy import QtWidgets

from .utils import newIcon
from pcbdet import __appname__
from pcbdet import __version__
from pcbdet.app import MainWindow, SigninDialog, SignupDialog


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

    # 设置登录窗口
    login_ui = SigninDialog()
    # 校验是否验证通过
    login_ui_status = login_ui.exec_()
    if login_ui_status == QtWidgets.QDialog.Accepted:
        win = MainWindow()
        win.show()
        win.raise_()
        sys.exit(app.exec_())
    else:
        signup_ui = SignupDialog()
        signup_ui_status = signup_ui.exec_()
        if signup_ui_status == QtWidgets.QDialog.Accepted:
            win = MainWindow()
            win.show()
            win.raise_()
            sys.exit(app.exec_())

# this main block is required to generate executable by pyinstaller
if __name__ == "__main__":
    main()
