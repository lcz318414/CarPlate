from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import *
from PySide2.QtCore import *
import cv2
from threading import Thread
from hyperlpr import pipline as pp
import SqlTools
import SerPort
import PlateInput
import time


class MainFormUI(QWidget):
    def __init__(self):
        # 从文件中加载UI定义
        super(MainFormUI, self).__init__()

        # 定义一些属性
        self.taken_photo_flag = 0
        self.price = 2
        self.device_init = False
        # 从 UI 定义中动态 创建一个相应的窗口对象
        # 注意：里面的控件对象也成为窗口对象的属性了
        # 比如 self.ui.button , self.ui.textEdit
        self.ui = QUiLoader().load('../Gui/MainForm.ui')
        # 载入子页面
        self.ser_config = SerPort.SerPortTools()
        self.plate_input = PlateInput.PlateInputTools()
        self.sql_tools = SqlTools.Tools()
        # 界面设置
        self.ui.statusbar.addWidget(self.ui.label_3)
        self.ui.statusbar.addWidget(self.ui.label_2)
        self.ui.label_2.setAutoFillBackground(True)  # 设置背景充满，为设置背景颜色的必要条件
        self.set_label_2_color('red')
        # 跳转相关界面
        self.ui.action_5.triggered.connect(self.open_plate_input)  # 录入车牌
        self.ui.action_8.triggered.connect(self.open_ser_config)  # 串口设置
        # 按钮设置
        self.ui.pushButton.setEnabled(False)
        self.ui.pushButton_2.setEnabled(False)
        self.ui.pushButton_3.setEnabled(False)
        self.ui.pushButton_4.setEnabled(False)

        self.ui.pushButton.clicked.connect(self.button1_clicked)
        self.ui.pushButton_2.clicked.connect(self.button2_clicked)
        self.ui.pushButton_3.clicked.connect(self.button3_clicked)
        self.ui.pushButton_4.clicked.connect(self.button4_clicked)
        #self.ui.pushButton_5.clicked.connect(self.button5_clicked)
        # 测试用
        # self.ui.pushButton_5.clicked.connect(self.button_clicked)


        # 创建线程
        self.thead = Thread(target=self.update_serial_info, name=None)
        self.thead.setDaemon(True)  # 设置为守护线程
        self.thead.start()  # 启动串口监听

        # 创建定时器
        self.timer = QTimer()  # 显示时间
        self.timer.timeout.connect(self.showTime)
        self.timer.start(1000)

        self.timer_1 = QTimer()  # 检测是否需要拍照
        self.timer_1.timeout.connect(self.take_photo)
        # self.timer_1.start(100)

    def test(self):
        # print(test.list_ports())
        self.take_photo()

    def open_ser_config(self):
        self.ser_config.ui.show()

    def open_plate_input(self):
        self.plate_input.ui.show()

    def openfile(self):
        openfile_name, _ = QFileDialog.getOpenFileName(self.ui, '选择文件', '', 'Jpeg files(*.jpg , *.jpeg)')
        return openfile_name

    def start_check(self, file):
        image = cv2.imread(file)
        image, res = pp.SimpleRecognizePlate(image)
        try:
            self.ui.label.setText(res[0])
        except Exception as e:
            self.ui.plainTextEdit.appendPlainText('抱歉，未检测到车牌...')
            self.ui.plainTextEdit.appendPlainText('---------------------------')
            return e
        self.ui.label.adjustSize()
        check_res = self.sql_tools.check_plate(res[0])
        print(check_res)
        if check_res[0]:
            if check_res[1][4] == '0':
                now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                self.ui.plainTextEdit.appendPlainText('车牌号:{}\n进入时间:{}'.format(check_res[1][1], now_time))
                self.sql_tools.update_intime_plate_info(now_time, check_res[1][0])
                self.ui.plainTextEdit.appendPlainText('匹配成功，正在下发抬杆指令...')
                self.open_the_door()
                time.sleep(0.01)
                self.ui.plainTextEdit.appendPlainText('下发成功，正在抬杆')
                self.ui.plainTextEdit.appendPlainText('---------------------------')
            elif check_res[1][4] == '1':
                now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                in_time = time.mktime(time.strptime(check_res[1][2], "%Y-%m-%d %H:%M:%S"))
                out_time = time.mktime(time.strptime(now_time, "%Y-%m-%d %H:%M:%S"))
                self.ui.plainTextEdit.appendPlainText('车牌号:{}\n进入时间:{}'.format(check_res[1][1], check_res[1][2]))
                self.ui.plainTextEdit.appendPlainText('驶出时间:{}'.format(now_time))
                stop_time = out_time - in_time
                stop_time_day = int(stop_time / 86400)
                stop_time_hour = int((stop_time % 86400) / 3600)
                stop_time_min = int(((stop_time % 86400) % 3600) / 60)
                str_stop_time = "已停车{}天{}时{}分，请缴费{}元".format(stop_time_day, stop_time_hour, stop_time_min, 2)
                self.ui.plainTextEdit.appendPlainText(str_stop_time)
                self.ui.plainTextEdit.appendPlainText('欢迎再次光临，正在下发抬杆指令...')
                self.open_the_door()
                time.sleep(0.01)
                self.ui.plainTextEdit.appendPlainText('下发成功，正在抬杆')
                self.ui.plainTextEdit.appendPlainText('---------------------------')
                self.sql_tools.update_outime_plate_info(now_time, check_res[1][0])
        else:
            self.ui.plainTextEdit.appendPlainText('外来车辆，不予抬杆...')
            self.ui.plainTextEdit.appendPlainText('---------------------------')

    def set_label_2_color(self, color):
        pe = QPalette()
        # pe.setColor(QPalette.WindowText, Qt.red)  # 设置字体颜色
        if color == 'red':
            pe.setColor(QPalette.Window, Qt.red)  # 设置背景颜色
            self.ui.label_2.setPalette(pe)
        else:
            pe.setColor(QPalette.Window, Qt.green)  # 设置背景颜色
            self.ui.label_2.setPalette(pe)

    def button1_clicked(self):
        self.timer_1.start(100)
        self.start_work()

    def button2_clicked(self):
        self.timer_1.stop()
        self.stop_work()

    def button3_clicked(self):
        self.manual_open()

    def button4_clicked(self):
        self.always_open()

    # def button5_clicked(self):
    #     self.always_open()

    def showTime(self):
        # 获取系统当前时间
        now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.ui.label_3.setText('当前时间:{}'.format(now_time))
        if self.ser_config.is_open:
            self.set_label_2_color('green')
            self.ui.label_2.setText('设备状态:已连接')
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton_2.setEnabled(True)
            self.ui.pushButton_3.setEnabled(True)
            self.ui.pushButton_4.setEnabled(True)

        else:
            self.set_label_2_color('red')
            self.ui.label_2.setText('设备状态:未连接')
            self.ui.pushButton.setEnabled(False)
            self.ui.pushButton_2.setEnabled(False)
            self.ui.pushButton_3.setEnabled(False)
            self.ui.pushButton_4.setEnabled(False)

    def open_the_door(self):
        data = b'\x00'
        self.ser_config.send_mess(data)

    def close_the_door(self):
        data = b'\x01'
        self.ser_config.send_mess(data)

    def start_work(self):
        data = b'\x02'
        self.ser_config.send_mess(data)

    def stop_work(self):
        data = b'\x03'
        self.ser_config.send_mess(data)

    def manual_open(self):
        data = b'\x04'
        self.ser_config.send_mess(data)

    # def manual_close(self):
    #     data = b'\x05'
    #     self.ser_config.send_mess(data)

    def always_open(self):
        data = b'\x05'
        self.ser_config.send_mess(data)

    def take_photo(self):
        if self.taken_photo_flag:
            self.taken_photo_flag = 0
            cap = cv2.VideoCapture(0)
            success, img = cap.read()
            cap.release()
            frame = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            show_img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.ui.label_4.setPixmap(QPixmap.fromImage(show_img))
            if success:
                time.sleep(1)
                cv2.imwrite("image2.jpg", img)
                self.start_check('image2.jpg')

    def update_serial_info(self):
        while True:
            while self.ser_config.is_open:
                try:
                    serial_info = self.ser_config.recieve_mess()
                    if serial_info != '':
                        # rec_mess = (str(serial_info, encoding='utf-8'))
                        hex2str = [hex(x) for x in bytes(serial_info)][0]
                        if hex2str == '0xff':  # 下位机发来拍照信号
                            if self.taken_photo_flag == 0:
                                # self.take_photo()
                                self.taken_photo_flag = 1
                except Exception as e:
                    print(e)
                    continue
            time.sleep(0.1)

    def paintEvent(self, e: QPaintEvent):
        painter = QPainter()
        painter.begin(self.ui)
        img = QImage()
        img.load('image2.jpg')
        painter.drawImage(QPoint(0, 0), img)
        painter.end()

    def closeEvent(self, event):
        """
        重写closeEvent方法，实现dialog窗体关闭时执行一些代码
        :param event: close()触发的事件
        :return: None
        """
        reply = QMessageBox.question(self.ui,
                                     '本程序',
                                     "是否要退出程序？",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    app = QApplication([])
    stats = MainFormUI()
    stats.ui.show()
    app.exec_()
