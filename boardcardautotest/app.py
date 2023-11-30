# -*- coding: utf-8 -*-
import sys
import functools
import math
import os
import os.path as osp
import re
import typing
import webbrowser
import glob
import json
from copy import deepcopy

import cv2 as cv

from qtpy import QtCore
from qtpy.QtCore import Qt, QSize, QRect
from qtpy import QtGui
from qtpy import QtWidgets

from .utils import ocr_processor

from boardcardautotest import __appname__

MAINWINDOW_H = 720
MAINWINDOW_W = 1080


class EmittingStr(QtCore.QObject):
    textWritten = QtCore.Signal(str)
    def write(self, text):
    #   text = f"({os.getcwd()})=> {text}\n"
      self.textWritten.emit(text)
      loop = QtCore.QEventLoop()
      QtCore.QTimer.singleShot(10, loop.quit)
      loop.exec_()

    def flush(self):
        pass


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        # self.resize(QSize(MAINWINDOW_W, MAINWINDOW_H))
        self.setWindowTitle(__appname__)

        self.show_image = None
        self.cap = cv.VideoCapture()  # 视频流
        self.CAM_NUM = 0

        # 输出重定向到 textbrowser
        sys.stdout = EmittingStr()
        sys.stdout.textWritten.connect(self.outputWritten)
        sys.stderr = EmittingStr()
        sys.stderr.textWritten.connect(self.outputWritten)

        # 日志输出
        self.log_dock_widget = LogDockWidget()
        self.addDockWidget(Qt.RightDockWidgetArea, self.log_dock_widget)

        # 菜单栏
        menubar = self.menuBar()
        self.mufiles = menubar.addMenu('Files(&F)')
        self.muedit = menubar.addMenu('Edit(&E)')
        
        muopenimagedir = QtWidgets.QAction('OpenImage(&I)', self)
        muopenimagedir.setShortcut('I')
        # self.muopenimagedir.triggered.connect(self.open_image_dir)
        self.mufiles.addAction(muopenimagedir)

        # 展示视频帧
        self.show_video_dock_widget = ShowVideoDockWidget()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.show_video_dock_widget)

        # 展示捕获图像 以子窗口形式
        self.show_image_widget = ShowImageWidget()

        # 按钮
        self.button_dock_Widget = ButtonDockWidget()
        self.addDockWidget(Qt.RightDockWidgetArea, self.button_dock_Widget)
        self.button_dock_Widget.buttonwidget.button_open_camera.clicked.connect(self.button_open_camera_clicked)
        self.button_dock_Widget.buttonwidget.button_capture_image.clicked.connect(self.button_capture_image_clicked)
        
        # 定时器，用于控制显示视频的帧率
        self.timer_camera = QtCore.QTimer()
        self.timer_camera.timeout.connect(self.show_camera)  # 若定时器结束，则调用show_camera()

    def outputWritten(self, text):
        cursor = self.log_dock_widget.textBrowser.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.log_dock_widget.textBrowser.setTextCursor(cursor)
        self.log_dock_widget.textBrowser.ensureCursorVisible()


    def button_open_camera_clicked(self):
        if self.timer_camera.isActive() == False:  # 若定时器未启动
            flag = self.cap.open(self.CAM_NUM)  # 参数是 0，表示打开笔记本的内置摄像头，参数是视频文件路径则打开视频
            if flag == False:  # flag 表示 open() 成不成功
                msg = QtWidgets.QMessageBox.warning(self, 'warning', "请检查相机与电脑是否连接正确", buttons=QtWidgets.QMessageBox.Ok)
            else:
                self.timer_camera.start(30)  # 定时器开始计时 30ms，结果是每过 30ms 从摄像头中取一帧显示
                self.button_dock_Widget.buttonwidget.button_open_camera.setText('Close Camera')
                print("===> Open Camera...")
        else:
            self.timer_camera.stop()  # 关闭定时器
            self.cap.release()  # 释放视频流
            self.show_video_dock_widget.show_area.clear()  # 清空视频显示区域
            self.show_video_dock_widget.show_area.setText("Video Show")    # 显示文字
            self.button_dock_Widget.buttonwidget.button_open_camera.setText('Open Camera')
            print("===> Close Camera...")
 
    def show_camera(self):
        _, self.image = self.cap.read()  # 从视频流中读取
        scale = round(self.height() / max(self.image.shape[0], self.image.shape[1]), 1)
        show = cv.cvtColor(self.image, cv.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色
        self.show_image = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成 QImage 形式
        self.show_video_dock_widget.show_area.setPixmap(
            QtGui.QPixmap.fromImage(self.show_image).scaled(
                self.image.shape[1]*scale, self.image.shape[0]*scale))  # 往显示视频的 Label 里显示 QImage

    def closeEvent(self, event):
        a = QtWidgets.QMessageBox.question(self, '是否退出', '确定要退出吗?', 
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                                           QtWidgets.QMessageBox.No)
        if a == QtWidgets.QMessageBox.Yes:
            self.show_image_widget.close()
            event.accept()
        else:
            event.ignore()

    def button_capture_image_clicked(self):
        if self.cap.isOpened():
            self.show_image_widget.setPixmap(QtGui.QPixmap.fromImage(self.show_image))
            self.show_image_widget.show()
            print("===> Capture Image...")
            # 开始对捕获的图像执行 OCR 检测
            orc_txt = ocr_processor(self.image)
            print("===> OCR detection result: ", orc_txt)


class ButtonWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ButtonWidget, self).__init__()
        # self.switch_button = SwitchButton()
        spacer_item = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        
        self.button_open_camera = QtWidgets.QPushButton("Open Camera", self)

        self.button_capture_image = QtWidgets.QPushButton("Capture Image", self)

        layout = QtWidgets.QVBoxLayout()
        layout.addSpacerItem(spacer_item)
        layout.addWidget(self.button_open_camera, 2)
        layout.addWidget(self.button_capture_image, 2)
        self.setLayout(layout)

    def capture_image(self):
        print("===> Capture Image")


class ButtonDockWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super(ButtonDockWidget, self).__init__()
        self.buttonwidget = ButtonWidget()
        self.setWidget(self.buttonwidget)
        self.setWindowTitle("Buttons")


class LogDockWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super(LogDockWidget, self).__init__()
        self.textBrowser = QtWidgets.QTextBrowser()
        self.setWidget(self.textBrowser)
        self.setWindowTitle("Logs")


class ShowVideoDockWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super(ShowVideoDockWidget, self).__init__()
        self.show_area = QtWidgets.QLabel()
        self.show_area.setText("Video Show")    # 显示文字
        # self.show_area.setFixedSize(size_w, size_h)

        # self.show_area.setScaledContents(True)
        self.show_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_area.setStyleSheet("""
                                        background-color: #808080;
                                        color: #CC7443;
                                        font-family: Titillium;
                                        font-size: 60px;
                                        """)

        self.setWidget(self.show_area)
        self.setWindowTitle("Videos")


class ShowImageWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ShowImageWidget, self).__init__()
        self.setWindowTitle("Capture Image")
        self.scale = 1
        self.point = QtCore.QPoint(0, 0)
        self.start_pos = None
        self.end_pos = None
        self.current_point_x = 0
        self.current_point_y = 0
        self.left_click = False     # 左键被点击
        self.right_click = False    # 右键被点击
        self.painter = QtGui.QPainter() # 设置画笔
        self.setMouseTracking(True)     # 设置鼠标跟踪(不需要按下就可跟踪)
    
    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.left_click = True
            self.start_pos = event.pos()
            print(f"===> Clicked left mouse: ({event.pos().x()}, {event.pos().y()})")

        if event.buttons() == Qt.RightButton:
            self.right_click = True
            self.start_pos = event.pos()
            print(f"===> Clicked right mouse: ({event.pos().x()}, {event.pos().y()})")
        
        print("===> scale: ", self.scale)
        print("===> image_posion: ", int(self.current_point_x/self.scale-self.point.x()), int(self.current_point_y/self.scale-self.point.y()))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.left_click = False
        if event.button() == Qt.RightButton:
            self.right_click = False
    
    def mouseMoveEvent(self, event):
        # self.hasMouseTracking()
        self.current_point_x = event.pos().x()
        self.current_point_y = event.pos().y()
        # print("===> current_point: ", self.current_point_x, self.current_point_y)
        self.update()
        if self.left_click:
            self.end_pos = event.pos() - self.start_pos
            self.point = self.point + self.end_pos
            self.start_pos = event.pos()
            self.repaint()
    
    def paintEvent(self, event):
        self.painter.begin(self)
        
        self.painter.scale(self.scale, self.scale)
        self.painter.drawPixmap(self.point, self.pixmap)

        self.painter.setPen(QtGui.QPen(Qt.red, 1, Qt.DashLine))
        # 对于鼠标, 只有缩放因子影响鼠标的真实坐标
        # 对于图像, 缩放因子和平移因子共同影响图像的真实坐标
        self.painter.drawLine(self.current_point_x/self.scale, 0, self.current_point_x/self.scale, self.height()/self.scale)  # 竖直线
        self.painter.drawLine(0, self.current_point_y/self.scale, self.width()/self.scale, self.current_point_y/self.scale)  # 水平线
        if self.right_click:
            pass

        self.painter.end()
        self.update()

    def wheelEvent(self, event):
        angle = event.angleDelta() / 8  # 返回QPoint对象，为滚轮转过的数值，单位为1/8度
        angleY = angle.y()
        # 获取当前鼠标相对于view的位置
        if angleY > 0:
            self.scale *= 1.1
        else:  # 滚轮下滚
            self.scale *= 0.9
        self.adjustSize()
        self.update()


class SwitchButton(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SwitchButton, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        #self.resize(70, 30)
        # SwitchButtonstate：True is ON，False is OFF
        self.state = False
        self.setFixedSize(80, 40)

    def mousePressEvent(self, event):
        '''
        set click event for state change
        '''
        super(SwitchButton, self).mousePressEvent(event)
        self.state = False if self.state else True
        self.update()

    def paintEvent(self, event):
        '''Set the button'''
        super(SwitchButton, self).paintEvent(event)

        # Create a renderer and set anti-aliasing and smooth transitions
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        # Defining font styles
        font = QtGui.QFont("Arial")
        font.setPixelSize(self.height()//3)
        painter.setFont(font)
        # SwitchButton state：ON
        if self.state:
            # Drawing background
            painter.setPen(Qt.NoPen)
            brush = QtGui.QBrush(QtGui.QColor('#bd93f9'))
            painter.setBrush(brush)
            # Top left corner of the rectangle coordinate
            rect_x = 0
            rect_y = 0
            rect_width = self.width()
            rect_height = self.height()
            rect_radius = self.height()//2
            painter.drawRoundedRect(rect_x, rect_y, rect_width, rect_height, rect_radius, rect_radius)
            # Drawing slides circle
            painter.setPen(Qt.NoPen)
            brush.setColor(QtGui.QColor('#ffffff'))
            painter.setBrush(brush)
            # Phase difference pixel point
            # Top left corner of the rectangle coordinate
            diff_pix = 3
            rect_x = self.width() - diff_pix - (self.height()-2*diff_pix)
            rect_y = diff_pix
            rect_width = (self.height()-2*diff_pix)
            rect_height = (self.height()-2*diff_pix)
            rect_radius = (self.height()-2*diff_pix)//2
            painter.drawRoundedRect(rect_x, rect_y, rect_width, rect_height, rect_radius, rect_radius)

            # ON txt set
            painter.setPen(QtGui.QPen(QtGui.QColor('#ffffff')))
            painter.setBrush(Qt.NoBrush)
            painter.drawText(QRect(int(self.height()/3), int(self.height()/3.5), 50, 20), Qt.AlignLeft, 'ON')
        # SwitchButton state：OFF
        else:
            # Drawing background
            painter.setPen(Qt.NoPen)
            brush = QtGui.QBrush(QtGui.QColor('#525555'))
            painter.setBrush(brush)
            # Top left corner of the rectangle coordinate
            rect_x = 0
            rect_y = 0
            rect_width = self.width()
            rect_height = self.height()
            rect_radius = self.height()//2
            painter.drawRoundedRect(rect_x, rect_y, rect_width, rect_height, rect_radius, rect_radius)

            # Drawing slides circle
            pen = QtGui.QPen(QtGui.QColor('#999999'))
            pen.setWidth(1)
            painter.setPen(pen)
            # Phase difference pixel point
            diff_pix = 3
            # Top left corner of the rectangle coordinate
            rect_x = diff_pix
            rect_y = diff_pix
            rect_width = (self.height()-2*diff_pix)
            rect_height = (self.height()-2*diff_pix)
            rect_radius = (self.height()-2*diff_pix)//2
            painter.drawRoundedRect(rect_x, rect_y, rect_width, rect_height, rect_radius, rect_radius)

            # OFF txt set
            painter.setBrush(Qt.NoBrush)
            painter.drawText(QRect(int(self.width()*1/2), int(self.height()/3.5), 50, 20), Qt.AlignLeft, 'OFF')
