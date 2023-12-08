import os
import os.path as osp

from qtpy import QtGui


here = osp.dirname(osp.abspath(__file__))

def newIcon(icon):
    icons_dir = osp.join(here, "../icons")
    return QtGui.QIcon(osp.join(":/", icons_dir, "%s.png" % icon))