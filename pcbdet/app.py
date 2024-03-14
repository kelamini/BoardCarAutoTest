# -*- coding: utf-8 -*-
import sys
import os
import os.path as osp
from copy import deepcopy
import datetime
import time

import cv2 as cv
from PyCameraList.camera_device import list_video_devices

from qtpy import QtCore
from qtpy.QtCore import Qt, QRect
from qtpy import QtGui
from qtpy import QtWidgets

from .utils import ocr_processor
from .utils import object_detection, visualize_object
from .utils import face_detection, visualize_face
from .database import PcbdetDataBase

from pcbdet import __appname__

current_time = time.strftime('%Y-%m-%d %H:%M:%S')

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('欢迎使用 PCB 缺陷检测系统')
        self.resize(300, 200)
        self.setFixedSize(self.width(), self.height())
        self.setWindowFlags(Qt.WindowCloseButtonHint)  # 设置隐藏关闭X的按钮

        # 加载数据库，初始化用户表
        self.pcbdet_database = PcbdetDataBase()
        self.pcbdet_database.init_user_table()


        # 定义界面控件设置
        # self.frame = QtWidgets.QFrame(self)  # 初始化 Frame对象
        self.verticalLayout = QtWidgets.QVBoxLayout()  # 设置垂直布局

        # 定义用户名输入框
        self.sign_in_label = QtWidgets.QLabel("账户：")
        self.sign_in_id = QtWidgets.QLineEdit()
        self.sign_in_id.setPlaceholderText("请输入账户名")
        sign_in_hlayout = QtWidgets.QHBoxLayout()
        sign_in_hlayout.addWidget(self.sign_in_label, 2)
        sign_in_hlayout.addWidget(self.sign_in_id, 7)
        self.verticalLayout.addLayout(sign_in_hlayout)

        # 定义密码输入框
        self.passwd_label = QtWidgets.QLabel("密码：")
        self.passwd = QtWidgets.QLineEdit()
        self.passwd.setPlaceholderText("请输入密码")
        self.passwd.setEchoMode(QtWidgets.QLineEdit.Password)
        passwd_hlayout = QtWidgets.QHBoxLayout()
        passwd_hlayout.addWidget(self.passwd_label, 2)
        passwd_hlayout.addWidget(self.passwd, 7)
        self.verticalLayout.addLayout(passwd_hlayout)

        # 定义登录按钮
        self.button_signin = QtWidgets.QPushButton()
        self.button_signin.setText("登录")
        # self.verticalLayout.addWidget(self.button_sign_in)

        # 定义注册按钮
        self.button_signup = QtWidgets.QPushButton()  
        self.button_signup.setText("注册")

        button_hlayout = QtWidgets.QHBoxLayout()
        button_hlayout.addWidget(self.button_signin)
        button_hlayout.addWidget(self.button_signup)
        self.verticalLayout.addLayout(button_hlayout)

        # 定义退出按钮
        self.button_quit = QtWidgets.QPushButton()
        self.button_quit.setText("退出")
        self.verticalLayout.addWidget(self.button_quit)

        self.setLayout(self.verticalLayout)

        # 绑定按钮事件
        self.button_signin.clicked.connect(self.button_sign_in_verify)
        self.button_quit.clicked.connect(
            QtCore.QCoreApplication.instance().quit)  # 返回按钮绑定到退出

    # 点击登录按钮校验信息
    def button_sign_in_verify(self):
        # 校验账号是否正确
        account_info = self.sign_in_id.text()
        passwd_info = self.passwd.text()
        admin_info = self.pcbdet_database.pcbdet_cursor.execute(f"SELECT * FROM uesr_info WHERE UserID==1").fetchall()
        if account_info != admin_info[0][2]:
            error_info = "Error! No account found, please register..."
            # self.popwindow_sign_in_error(error_info)
            print(f"[{current_time}] 错误：账号输入错误或者不存在，请重新输入或注册")
            return
        # 校验密码是否正确
        if passwd_info != admin_info[0][3]:
            error_info = "Error! Password entered incorrectly..."
            # self.popwindow_sign_in_error(error_info)
            print(f"[{current_time}] 错误：密码输入错误，请重新输入")
            return

        self.accept()   # 验证通过，设置 QDialog 对象状态为允许
        print(f"[{current_time}] 登录成功！")
        self.pcbdet_database.close_user_table()

    # def popwindow_sign_in_error(self, info):
    #     QtWidgets.QMessageBox.information(self, info, QtWidgets.QMessageBox.Yes)


class EmittingStr(QtCore.QObject):
    textWritten = QtCore.Signal(str)
    def write(self, text):
    #   text = f"({os.getcwd()})=> {text}"
      self.textWritten.emit(text)
      loop = QtCore.QEventLoop()
      QtCore.QTimer.singleShot(10, loop.quit)
      loop.exec_()

    def flush(self):
        pass


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        self.image = None
        self.post_image = None
        self.post_qimage = None
        self.capture_image = None
        self.save_default_dir = None
        self.cap = cv.VideoCapture()  # 视频流
        self.CAM_NUM = 0
        camera_devices = list_video_devices()
        if len(camera_devices) != 0:
            self.CAM_NUM = int(camera_devices[0][0])    # 相机设备编号
        self.detect_mode = True

        # ----------------------- 菜单栏 -----------------------
        menubar = self.menuBar()
        
        self.mufiles = menubar.addMenu('Files(&F)')
        muopenimagedir = QtWidgets.QAction('OpenImage(&I)', self)
        muopenimagedir.setShortcut('I')
        # muopenimagedir.triggered.connect(self.open_image_dir)
        self.mufiles.addAction(muopenimagedir)

        self.muedit = menubar.addMenu('Edit(&E)')
        # ----------------------- end -----------------------

        # ----------------------- 输出重定向到 textbrowser -----------------------
        sys.stdout = EmittingStr()
        sys.stdout.textWritten.connect(self.outputWritten)
        sys.stderr = EmittingStr()
        sys.stderr.textWritten.connect(self.outputWritten)
        # ----------------------- end -----------------------

        # ----------------------- 日志输出 -----------------------
        self.log_dock_widget = LogDockWidget()
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock_widget)
        # ----------------------- end -----------------------

        # ----------------------- 展示视频帧 -----------------------
        self.show_video_dock_widget = ShowVideoDockWidget()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.show_video_dock_widget)
        # ----------------------- end -----------------------

        # ----------------------- 展示捕获图像 以弹出子窗口形式 -----------------------
        self.show_image_dialog = ShowImageDialog()
        # ----------------------- end -----------------------

        # ----------------------- 按钮 -----------------------
        self.button_dock_Widget = ButtonDockWidget()
        self.addDockWidget(Qt.RightDockWidgetArea, self.button_dock_Widget)
        self.button_dock_Widget.buttonwidget.button_open_camera.clicked.connect(self.open_camera_clicked)
        self.button_dock_Widget.buttonwidget.button_capture_image.clicked.connect(self.capture_image_clicked)
        # self.button_dock_Widget.buttonwidget.checkbox_ocr_detection.clicked.connect(self.ocr_auto_detection)
        self.button_dock_Widget.buttonwidget.checkbox_binary_image.clicked.connect(self.show_binary_image)
        self.button_dock_Widget.buttonwidget.spinbox_for_binary_image.valueChanged.connect(self.valuechange_for_binary_image)
        self.button_dock_Widget.buttonwidget.button_set_save_dir.clicked.connect(self.set_default_directory)
        self.button_dock_Widget.buttonwidget.combobox_for_camera_devices.currentIndexChanged.connect(self.set_camera_id)
        self.button_dock_Widget.buttonwidget.button_open_database.clicked.connect(self.open_database_clicked)
        self.button_dock_Widget.buttonwidget.button_detect_begin.clicked.connect(self.detect_clicked)
        self.button_dock_Widget.buttonwidget.combobox_for_detect.currentIndexChanged.connect(self.set_detect_mode)
        self.button_dock_Widget.buttonwidget.combobox_for_load_model.currentIndexChanged.connect(self.set_delect_model)

        self.show_image_dialog.button_save_image.clicked.connect(self.save_image)
        self.show_image_dialog.button_draw_rectangle.clicked.connect(self.draw_rectangle)

        # ----------------------- end -----------------------
        
        # ----------------------- 定时器 用于控制显示视频的帧率 -----------------------
        self.timer_camera = QtCore.QTimer()
        self.timer_camera.timeout.connect(self.camera_image_process)  # 若定时器结束，则调用show_camera()
        # ----------------------- end -----------------------

    def open_database_clicked(self):
        self.database = DatabaseWidget()
        self.database.show()
        print(f"[{current_time}] 已打开数据库")

    def detect_clicked(self):
        if self.detect_mode == True:
            if self.button_dock_Widget.buttonwidget.button_detect_begin.text() == "关闭检测":
                self.button_dock_Widget.buttonwidget.button_detect_begin.setText('开始检测')
                print(f"[{current_time}] 已关闭自动检测")
            else:
                flag = True
                if flag == False:
                    QtWidgets.QMessageBox.warning(self, 'Warning', "模型加载错误，请确保模型已经下载！", buttons=QtWidgets.QMessageBox.Ok)
                else:
                    self.button_dock_Widget.buttonwidget.button_detect_begin.setText('关闭检测')
                    print(f"[{current_time}] 开始执行自动检测")
        else:
            # self.button_dock_Widget.buttonwidget.button_detect_begin.setText('单次检测')
            print(f"[{current_time}] 开始执行单次检测")

    def set_detect_mode(self, text):
        if self.button_dock_Widget.buttonwidget.combobox_for_detect.currentText() == "自动":
            self.detect_mode = True
            self.button_dock_Widget.buttonwidget.button_detect_begin.setText('开始检测')
        else:
            self.detect_mode = False
            self.button_dock_Widget.buttonwidget.button_detect_begin.setText('单次检测')

    def set_delect_model(self, text):
        model_name = self.button_dock_Widget.buttonwidget.combobox_for_load_model.currentText()
        print(f"[{current_time}] 当前选择的模型是：{model_name}")

    def set_camera_id(self, trxt):
        camera_device = self.button_dock_Widget.buttonwidget.combobox_for_camera_devices.currentText()
        self.CAM_NUM = camera_device.split("-")[1]
        print(f"[{current_time}] 已设置相机设备: {camera_device}")

    def outputWritten(self, text):
        cursor = self.log_dock_widget.textBrowser.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.log_dock_widget.textBrowser.setTextCursor(cursor)
        self.log_dock_widget.textBrowser.ensureCursorVisible()

    def closeEvent(self, event):
        a = QtWidgets.QMessageBox.question(self, '是否退出', '确定要退出吗?', 
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                                           QtWidgets.QMessageBox.No)
        if a == QtWidgets.QMessageBox.Yes:
            self.show_image_dialog.close()
            event.accept()
        else:
            event.ignore()

    def open_camera_clicked(self):
        if self.timer_camera.isActive() == False:  # 若定时器未启动
            flag = self.cap.open(self.CAM_NUM)  # 参数是 0，表示打开笔记本的内置摄像头，参数是视频文件路径则打开视频
            if flag == False:  # flag 表示 open() 成不成功
                msg = QtWidgets.QMessageBox.warning(self, 'warning', "请检查相机与电脑是否连接正确", buttons=QtWidgets.QMessageBox.Ok)
            else:
                self.timer_camera.start(30)  # 定时器开始计时 30ms，结果是每过 30ms 从摄像头中取一帧显示
                self.button_dock_Widget.buttonwidget.button_open_camera.setText('关闭相机')
                print(f"[{current_time}] 已打开相机")
        else:
            self.timer_camera.stop()  # 关闭定时器
            self.cap.release()  # 释放视频流
            self.show_video_dock_widget.show_area.clear()  # 清空视频显示区域
            self.show_video_dock_widget.show_area.setText("视频显示区")    # 显示文字
            self.button_dock_Widget.buttonwidget.button_open_camera.setText('打开相机')
            print(f"[{current_time}] 已关闭相机")
 
    def camera_image_process(self):
        _, self.image = self.cap.read()
        self.post_image = deepcopy(self.image)

        # # 执行目标检测
        # if self.button_dock_Widget.buttonwidget.checkbox_object_detection.isChecked():
        #     th = self.button_dock_Widget.buttonwidget.spinbox_for_object_detection_th.value()
        #     detection_result = object_detection(self.image, th)
        #     self.post_image = visualize_object(self.post_image, detection_result)

        # # 执行人脸检测
        # if self.button_dock_Widget.buttonwidget.checkbox_face_detection.isChecked():
        #     conf = self.button_dock_Widget.buttonwidget.spinbox_for_face_detection_conf.value()
        #     th = self.button_dock_Widget.buttonwidget.spinbox_for_face_detection_th.value()
        #     detection_result = face_detection(self.image, conf, th)
        #     self.post_image = visualize_face(self.post_image, detection_result)

        # 翻转图像
        if self.button_dock_Widget.buttonwidget.button_original_image.isChecked():
            self.post_image = self.post_image
            # print(f"[{current_time}] 切换到原始图像")
        elif self.button_dock_Widget.buttonwidget.button_horizontal_image.isChecked():
            self.post_image = cv.flip(self.post_image, 1)
            # print(f"[{current_time}] 切换到水平翻转图像")
        elif self.button_dock_Widget.buttonwidget.button_vertical_image.isChecked():
            self.post_image = cv.flip(self.post_image, 0)
            # print(f"[{current_time}] 切换到垂直翻转图像")
        elif self.button_dock_Widget.buttonwidget.button_hv_image.isChecked():
            self.post_image = cv.flip(self.post_image, -1)
            # print(f"[{current_time}] 切换到完全翻转图像")

        # 转换到二值图
        if self.button_dock_Widget.buttonwidget.checkbox_binary_image.isChecked():
            image_gray = cv.cvtColor(self.post_image, cv.COLOR_BGR2GRAY)
            th = self.button_dock_Widget.buttonwidget.spinbox_for_binary_image.value()
            _, self.post_image = cv.threshold(image_gray, th, 255, cv.THRESH_BINARY) # cv.THRESH_BINARY+cv.THRESH_OTSU
        
        if len(self.post_image.shape) == 3:  # 三通道
            rgb_image = cv.cvtColor(self.post_image, cv.COLOR_BGR2RGB)  # 视频色彩转换回 RGB，这样才是现实的颜色
            self.post_qimage = QtGui.QImage(rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成 QImage 形式
        else:   # 单通道
            self.post_qimage = QtGui.QImage(self.post_image.data, self.post_image.shape[1], self.post_image.shape[0], QtGui.QImage.Format_Indexed8)

        scale = round(self.height() / max(self.image.shape[0], self.image.shape[1]), 1)
        self.show_video_dock_widget.show_area.setPixmap(
            QtGui.QPixmap.fromImage(self.post_qimage).scaled(
                int(self.image.shape[1]*scale), int(self.image.shape[0]*scale)))
        
        # # 执行 OCR 检测
        # if self.button_dock_Widget.buttonwidget.checkbox_ocr_detection.isChecked():
        #     orc_txt = ocr_processor(self.image)
        #     if orc_txt.rstrip():
        #         print("===> OCR detection result: \n", orc_txt)


    def capture_image_clicked(self):
        if self.cap.isOpened():
            self.capture_image = deepcopy(self.post_image)
            self.show_image_dialog.show_image_widget.setPixmap(QtGui.QPixmap.fromImage(self.post_qimage))
            self.show_image_dialog.show()
            print(f"[{current_time}] 已捕获图像")
            # # 开始对捕获的图像执行 OCR 检测
            # orc_txt = ocr_processor(self.image)
            # print("===> OCR detection result: ", orc_txt)
        else:
            self.popwindow_opened_camera()
            print(f"[{current_time}] 错误! 请打开相机")

    def ocr_auto_detection(self):
        if self.button_dock_Widget.buttonwidget.checkbox_ocr_detection.isChecked():
            print(f"[{current_time}] 正在打开 OCR 自动检测...")
        else:
            print(f"[{current_time}] 关闭 OCR 自动检测...")

    def show_binary_image(self):
        if self.button_dock_Widget.buttonwidget.checkbox_binary_image.isChecked():
            print(f"[{current_time}] 显示二值图...")
        else:
            print(f"[{current_time}] 显示 RGB 图...")


    def valuechange_for_binary_image(self):
        print(f"[{current_time}] 当前阈值: {self.button_dock_Widget.buttonwidget.spinbox_for_binary_image.value()}")

    def popwindow_closed_camera(self):
        QtWidgets.QMessageBox.information(self, "Error!", "Please closing Camera.",
                                QtWidgets.QMessageBox.Yes)

    def popwindow_opened_camera(self):
        QtWidgets.QMessageBox.information(self, "Error!", "Please opening Camera.",
                                QtWidgets.QMessageBox.Yes)

    def set_default_directory(self):
        if not self.cap.isOpened():
            self.save_default_dir = QtWidgets.QFileDialog.getExistingDirectory(None, "请选择文件路径", os.getcwd())
            print(f"[{current_time}] 设置保存路径: '{self.save_default_dir}'")
        else:
            self.popwindow_closed_camera()
            print(f"[{current_time}] 错误! 请关闭相机")

    def popwindow_saved_error(self):
        QtWidgets.QMessageBox.information(self, "Error!", "Not set save directory.",
                                QtWidgets.QMessageBox.Yes)
    
    def popwindow_saved_succeed(self, message):
        QtWidgets.QMessageBox.information(self, "Successful!", f"Image saved to: '{message}'",
                                QtWidgets.QMessageBox.Yes)

    def save_image(self):
        if self.save_default_dir:
            filename = "_".join([datetime.datetime.now().strftime("%Y%m%d%H%M%S"), str(datetime.datetime.now().timestamp())])+'.jpg'
            save_path = osp.join(self.save_default_dir, filename)
            cv.imwrite(save_path, self.capture_image)
            
            self.popwindow_saved_succeed(save_path)
            print(f"[{current_time}] 图像保存到: '{save_path}'")
        else:
            self.popwindow_saved_error()
            print(f"[{current_time}] 错误! 请设置默认保存路径.")

    def draw_rectangle(self):
        print(f"[{current_time}] 绘制矩形...")
        self.show_image_dialog.show_image_widget.draw_status = 'rectangle'


class ButtonWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ButtonWidget, self).__init__()
        # 弹簧
        spacer_item = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        # label
        self.label_for_binary_image_th = QtWidgets.QLabel("阈值: ", self)
        # self.label_for_object_detection_th = QtWidgets.QLabel("Th: ", self)
        # self.label_for_face_detection_conf = QtWidgets.QLabel("Conf: ", self)
        # self.label_for_face_detection_th = QtWidgets.QLabel("Th: ", self)
        self.label_for_exposure_mode = QtWidgets.QLabel("曝光模式: ", self)
        self.label_for_exposure_time = QtWidgets.QLabel("曝光时间: ", self)
        self.label_for_camera_gain = QtWidgets.QLabel("相机增益: ", self)
        self.label_for_brightness = QtWidgets.QLabel("光源亮度: ", self)
        self.label_for_serial_port = QtWidgets.QLabel("串口号: ", self)
        self.label_for_baud_rate = QtWidgets.QLabel("波特率: ", self)
        self.label_for_load_model = QtWidgets.QLabel("选择模型: ", self)
        self.label_for_camera_devices = QtWidgets.QLabel("选择相机: ", self)



        # push button
        self.button_open_camera = QtWidgets.QPushButton("打开相机", self)
        self.button_capture_image = QtWidgets.QPushButton("捕获图像", self)
        self.button_set_save_dir = QtWidgets.QPushButton("设置保存图像路径", self)
        self.button_set_serial_port = QtWidgets.QPushButton("扫描串口", self)
        self.button_detect_begin = QtWidgets.QPushButton("开始检测", self)
        self.button_open_database = QtWidgets.QPushButton("打开数据库", self)

        # radio button
        self.button_original_image = QtWidgets.QRadioButton("原始图像", self)
        self.button_original_image.setChecked(True)
        self.button_horizontal_image = QtWidgets.QRadioButton("水平翻转", self)
        self.button_vertical_image = QtWidgets.QRadioButton("垂直翻转", self)
        self.button_hv_image = QtWidgets.QRadioButton("完全翻转", self)

        # check box
        # self.checkbox_ocr_detection = QtWidgets.QCheckBox("OCR Auto Detection", self)
        self.checkbox_binary_image = QtWidgets.QCheckBox("切换二值图像", self)
        # self.checkbox_object_detection = QtWidgets.QCheckBox("Object Detection", self)
        # self.checkbox_face_detection = QtWidgets.QCheckBox("Face Detection", self)

        # combo box
        self.combobox_for_exposure_mode = QtWidgets.QComboBox()
        self.combobox_for_exposure_mode.addItem("自动")
        self.combobox_for_exposure_mode.addItem("手动")
        self.combobox_for_detect = QtWidgets.QComboBox()
        self.combobox_for_detect.addItem("自动")
        self.combobox_for_detect.addItem("单次")
        self.combobox_for_load_model = QtWidgets.QComboBox()
        self.combobox_for_load_model.addItem("pcb_detect_tiny")
        self.combobox_for_load_model.addItem("pcb_detect_small")
        self.combobox_for_load_model.addItem("pcb_detect_base")
        self.combobox_for_load_model.addItem("pcb_detect_large")
        self.combobox_for_camera_devices = QtWidgets.QComboBox()
        for device in list_video_devices():
            self.combobox_for_camera_devices.addItem(f"{device[1]}-{device[0]}")

        # line edit
        self.linedit_for_exposure_time = QtWidgets.QLineEdit()
        self.linedit_for_camera_gain = QtWidgets.QLineEdit("3")
        self.linedit_for_serial_port = QtWidgets.QLineEdit()
        self.linedit_for_baud_rate = QtWidgets.QLineEdit()

        # # slider
        # self.slider_for_binary_image = QtWidgets.QSlider(Qt.Horizontal)
        # self.slider_for_binary_image.setMinimum(0) # 设置最小值
        # self.slider_for_binary_image.setMaximum(255) # 设置最大值
        # self.slider_for_binary_image.setSingleStep(5)   # 步长
        # self.slider_for_binary_image.setValue(127)   # 设置初始值
        # self.slider_for_binary_image.setTickPosition(QtWidgets.QSlider.TicksBelow)  # 设置刻度的位置， 刻度在下方
        # self.slider_for_binary_image.setTickInterval(5) # 设置刻度的间隔
        self.slider_for_brightness = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_for_brightness.setMinimum(0) # 设置最小值
        self.slider_for_brightness.setMaximum(100) # 设置最大值
        self.slider_for_brightness.setSingleStep(5)   # 步长
        self.slider_for_brightness.setValue(75)   # 设置初始值
        self.slider_for_brightness.setTickPosition(QtWidgets.QSlider.TicksBelow)  # 设置刻度的位置， 刻度在下方
        self.slider_for_brightness.setTickInterval(5) # 设置刻度的间隔

        # ---------------------------- spin box ----------------------------
        # binary image
        self.spinbox_for_binary_image = QtWidgets.QSpinBox()
        self.spinbox_for_binary_image.setValue(127)     # 设置当前值
        self.spinbox_for_binary_image.setMinimum(0)     # 设置最小值
        self.spinbox_for_binary_image.setMaximum(255)   # 设置最大值
        # object detection
        self.spinbox_for_object_detection_th = QtWidgets.QSpinBox()
        self.spinbox_for_object_detection_th.setValue(50)     # 设置当前值
        self.spinbox_for_object_detection_th.setMinimum(0)     # 设置最小值
        self.spinbox_for_object_detection_th.setMaximum(100)   # 设置最大值
        # face detection
        self.spinbox_for_face_detection_th = QtWidgets.QSpinBox()
        self.spinbox_for_face_detection_th.setValue(50)     # 设置当前值
        self.spinbox_for_face_detection_th.setMinimum(0)     # 设置最小值
        self.spinbox_for_face_detection_th.setMaximum(100)   # 设置最大值
        self.spinbox_for_face_detection_conf = QtWidgets.QSpinBox()
        self.spinbox_for_face_detection_conf.setValue(50)     # 设置当前值
        self.spinbox_for_face_detection_conf.setMinimum(0)     # 设置最小值
        self.spinbox_for_face_detection_conf.setMaximum(100)   # 设置最大值
        # ---------------------------- end ----------------------------

        # -------------------------- 布局 --------------------------
        # flip image
        flip_hlayout_1 = QtWidgets.QHBoxLayout()
        flip_hlayout_1.addWidget(self.button_original_image)
        flip_hlayout_1.addWidget(self.button_hv_image)
        flip_hlayout_2 = QtWidgets.QHBoxLayout()
        flip_hlayout_2.addWidget(self.button_vertical_image)
        flip_hlayout_2.addWidget(self.button_horizontal_image)
        flip_vlayout = QtWidgets.QVBoxLayout()
        flip_vlayout.addLayout(flip_hlayout_1)
        flip_vlayout.addLayout(flip_hlayout_2)
        
        # binary image
        binary_image_layout = QtWidgets.QHBoxLayout()
        binary_image_layout.addWidget(self.checkbox_binary_image, 8)
        binary_image_layout.addWidget(self.label_for_binary_image_th, 1)
        binary_image_layout.addWidget(self.spinbox_for_binary_image, 1)

        # load model
        load_model_layout = QtWidgets.QHBoxLayout()
        load_model_layout.addWidget(self.label_for_load_model)
        load_model_layout.addWidget(self.combobox_for_load_model)


        # detect begin
        detect_layout = QtWidgets.QHBoxLayout()
        detect_layout.addWidget(self.button_detect_begin)
        detect_layout.addWidget(self.combobox_for_detect)

        # dtect camera devices
        camera_devices_layout = QtWidgets.QHBoxLayout()
        camera_devices_layout.addWidget(self.label_for_camera_devices)
        camera_devices_layout.addWidget(self.combobox_for_camera_devices)

        # # object detection
        # object_detection_layout = QtWidgets.QHBoxLayout()
        # object_detection_layout.addWidget(self.checkbox_object_detection, 8)
        # object_detection_layout.addWidget(self.label_for_object_detection_th, 1)
        # object_detection_layout.addWidget(self.spinbox_for_object_detection_th, 1)
        
        # # face detection
        # face_detection_layout = QtWidgets.QHBoxLayout()
        # face_detection_layout.addWidget(self.checkbox_face_detection, 16)
        # face_detection_layout.addWidget(self.label_for_face_detection_th, 1)
        # face_detection_layout.addWidget(self.spinbox_for_face_detection_th, 1)
        # face_detection_layout.addWidget(self.label_for_face_detection_conf, 1)
        # face_detection_layout.addWidget(self.spinbox_for_face_detection_conf, 1)

        # serial port
        serial_port_layout = QtWidgets.QHBoxLayout()
        serial_port_layout.addWidget(self.label_for_serial_port)
        serial_port_layout.addWidget(self.linedit_for_serial_port)

        # baud rate
        baud_rate_layout = QtWidgets.QHBoxLayout()
        baud_rate_layout.addWidget(self.label_for_baud_rate)
        baud_rate_layout.addWidget(self.linedit_for_baud_rate)

        # 串口配置
        serial_port_vlayout = QtWidgets.QVBoxLayout()
        serial_port_vlayout.addLayout(serial_port_layout)
        serial_port_vlayout.addLayout(baud_rate_layout)
        serial_port_vlayout.addWidget(self.button_set_serial_port)
        serial_port_group = QtWidgets.QGroupBox("串口配置区")
        serial_port_group.setLayout(serial_port_vlayout)

        # exposure mode
        exposure_mode_layout = QtWidgets.QHBoxLayout()
        exposure_mode_layout.addWidget(self.label_for_exposure_mode)
        exposure_mode_layout.addWidget(self.combobox_for_exposure_mode)

        # exposure time
        exposure_time_layout = QtWidgets.QHBoxLayout()
        exposure_time_layout.addWidget(self.label_for_exposure_time)
        exposure_time_layout.addWidget(self.linedit_for_exposure_time)

        # camera gain
        camera_gain_layout = QtWidgets.QHBoxLayout()
        camera_gain_layout.addWidget(self.label_for_camera_gain)
        camera_gain_layout.addWidget(self.linedit_for_camera_gain)

        # brightness of light
        brightness_layout = QtWidgets.QHBoxLayout()
        brightness_layout.addWidget(self.label_for_brightness)
        brightness_layout.addWidget(self.slider_for_brightness)

        # 相机光源配置区
        camera_vlayout = QtWidgets.QVBoxLayout()
        camera_vlayout.addLayout(camera_devices_layout)
        camera_vlayout.addLayout(exposure_mode_layout)
        camera_vlayout.addLayout(exposure_time_layout)
        camera_vlayout.addLayout(camera_gain_layout)
        camera_vlayout.addWidget(self.button_open_camera)
        camera_vlayout.addLayout(brightness_layout)
        camera_group = QtWidgets.QGroupBox("相机光源配置区")
        camera_group.setLayout(camera_vlayout)

        # 功能区
        function_vlayout = QtWidgets.QVBoxLayout()
        function_vlayout.addLayout(flip_vlayout)
        function_vlayout.addLayout(binary_image_layout)
        function_vlayout.addWidget(self.button_set_save_dir)
        function_vlayout.addWidget(self.button_capture_image)
        function_vlayout.addLayout(load_model_layout)
        function_vlayout.addLayout(detect_layout)
        function_vlayout.addWidget(self.button_open_database)
        function_group = QtWidgets.QGroupBox("功能区")
        function_group.setLayout(function_vlayout)

        # global
        global_layout = QtWidgets.QVBoxLayout()
        # global_layout.addSpacerItem(spacer_item)
        global_layout.addWidget(serial_port_group)
        global_layout.addWidget(camera_group)
        global_layout.addWidget(function_group)

        self.setLayout(global_layout)


class ButtonDockWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super(ButtonDockWidget, self).__init__()
        self.buttonwidget = ButtonWidget()
        self.setWidget(self.buttonwidget)
        self.setWindowTitle("配置区")


class LogDockWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super(LogDockWidget, self).__init__()
        self.textBrowser = QtWidgets.QTextBrowser()
        self.setWidget(self.textBrowser)
        self.setWindowTitle("日志")


class ShowVideoDockWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super(ShowVideoDockWidget, self).__init__()
        self.setWindowTitle("视频显示区")

        self.show_area = QtWidgets.QLabel()
        self.show_area.setText("视频显示区")    # 显示文字
        # self.show_area.setScaledContents(True)
        self.show_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_area.setStyleSheet("""
                                        background-color: #808080;
                                        color: #CC7443;
                                        font-family: Titillium;
                                        font-size: 60px;
                                        """)

        self.setWidget(self.show_area)


class ShowImageWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ShowImageWidget, self).__init__()
        self.setWindowTitle("捕获图像")
        self.pixmap = QtGui.QPixmap()
        self.scale = 1
        self.point = QtCore.QPoint(0, 0)            # 记录图像左上角点在显示框的位置坐标
        self.start_pos = QtCore.QPoint(0, 0)        # 记录鼠标点击坐标
        self.end_pos = QtCore.QPoint(0, 0)          # 记录拖动图像的偏移量
        self.current_point = QtCore.QPoint(0, 0)    # 记录当前(实时)鼠标位置坐标
        self.image_pos = QtCore.QPoint(0, 0)        # 记录点击点在图像上的真实坐标
        self.left_click = False             # 左键被点击
        self.right_click = False            # 右键被点击
        self.painter = QtGui.QPainter()     # 设置画笔
        self.setMouseTracking(True)         # 设置鼠标跟踪(不需要按下就可跟踪)
        self.draw_status = None     # 使用鼠标绘制图形 --> rectangle
    
    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.left_click = True
            self.start_pos = event.pos()
            self.image_pos = self.start_pos / self.scale - self.point
            print(f"[{current_time}] 点击鼠标左键: [{event.pos().x()}, {event.pos().y()}]")

        if event.buttons() == Qt.RightButton:
            self.right_click = True
            self.start_pos = event.pos()
            self.image_pos = self.start_pos / self.scale - self.point
            print(f"[{current_time}] 点击鼠标右键: [{event.pos().x()}, {event.pos().y()}]")
        
        print(f"[{current_time}] Scales: [{round(self.scale, 3)}]", )
        print(f"[{current_time}] Image Posion: [{int(self.image_pos.x())}, {int(self.image_pos.y())}]")
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.left_click = False
        if event.button() == Qt.RightButton:
            self.right_click = False
    
    def mouseMoveEvent(self, event):
        # self.hasMouseTracking()
        self.current_point = event.pos()
        self.update()
        if self.left_click:
            self.end_pos = event.pos() - self.start_pos
            self.point = self.point + self.end_pos
            self.start_pos = event.pos()
            self.repaint()
    
    def paintEvent(self, event):
        self.painter.begin(self)
        if self.pixmap:            
            self.painter.scale(self.scale, self.scale)
            self.painter.drawPixmap(self.point, self.pixmap)

            self.painter.setPen(QtGui.QPen(Qt.red, 1, Qt.DashLine))
            # 对于鼠标, 只有缩放因子影响鼠标的真实坐标
            # 对于图像, 缩放因子和平移因子共同影响图像的真实坐标
            self.painter.drawLine(int(self.current_point.x()/self.scale), 0, int(self.current_point.x()/self.scale), int(self.height()/self.scale))  # 竖直线
            self.painter.drawLine(0, int(self.current_point.y()/self.scale), int(self.width()/self.scale), int(self.current_point.y()/self.scale))  # 水平线
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


class ShowImageDialog(QtWidgets.QDialog):
    def __init__(self):
        super(ShowImageDialog, self).__init__()
        self.setWindowTitle("捕获图像")
        self.resize(640, 480)

        self.show_image_widget = ShowImageWidget()

        self.button_save_image = QtWidgets.QPushButton("保存图像", self)
        self.button_draw_rectangle = QtWidgets.QPushButton("绘制矩形", self)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.button_save_image)
        button_layout.addWidget(self.button_draw_rectangle)

        global_layout = QtWidgets.QVBoxLayout()
        global_layout.addWidget(self.show_image_widget)
        global_layout.addLayout(button_layout)
        
        self.setLayout(global_layout)


class DatabaseWidget(QtWidgets.QWidget):
    def __init__(self):
        super(DatabaseWidget, self).__init__()
        self.setWindowTitle("数据库")
        self.setMinimumSize(640, 480)
        defect_database = PcbdetDataBase()
        defect_database.init_defect_table()
        all_data = defect_database.fetch_all_data()
        table_name = defect_database.obt_table_name()

        # table widget
        raw_count = len(all_data)
        colm_count = len(table_name)
        self.database_table = QtWidgets.QTableWidget()
        self.database_table.setColumnCount(colm_count)
        self.database_table.setRowCount(raw_count)
        self.database_table.setHorizontalHeaderLabels(table_name)
        # 在表格中填充数据
        for raw in range(raw_count):
            for colm in range(colm_count):
                self.database_table.setItem(raw, colm, QtWidgets.QTableWidgetItem(str(all_data[raw][colm])))

        # button
        self.button_search_info = QtWidgets.QPushButton("关键字搜索")

        # line edit
        self.label_for_serach = QtWidgets.QLineEdit()
        # 布局
                
        function_layout = QtWidgets.QHBoxLayout()
        function_layout.addWidget(self.label_for_serach)
        function_layout.addWidget(self.button_search_info)

        global_layout = QtWidgets.QVBoxLayout()
        global_layout.addWidget(self.database_table)
        global_layout.addLayout(function_layout)
        
        self.setLayout(global_layout)


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
