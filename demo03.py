motor_type = 'ACS'
version = 0.031

# Demo GUI for stepper motor controllers v.0.03 
# including:
# - an EXTREMELY simple status logger (records the time of limit switch activation)
# - simple status monitor for all axes:
#	- current position (in microsteps)
#	- current status string:
#		- ready to move
#		- moving
#		- limit switch error
#		- status LED (green = OK, red = not OK, blinking = moving). LED widged is based on LedIndicator widget by Nick Lamprianidis
# - buttons for simple 'one long step' motion
# - buttons for 'stepwise' thread-driven movement (experiment simulation)
# - stop buttons

import newACS

axis_names = {1 : 'Standa 053067', 3 : 'PI Micos WT-85'}

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import sys
import time
from datetime import datetime

#from oldstanda import oldStandaDevices
from LedIndicatorWidget import LedIndicator

class motorLED(LedIndicator):
	def __init__(self, parent = None):
		LedIndicator.__init__(self, parent)
		self.setDisabled(True) # make it non-clickable
		self.turnGreen()
		self.turnOff()
		self.status = 'Off'
	
	def turnGreen(self): #COLOR CHANGE does not work properly without hide'n'show
		self.hide()
		self.on_color_1 = QColor(0, 255, 0)
		self.on_color_2 = QColor(0, 192, 0)
		self.off_color_1 = QColor(0, 28, 0)
		self.off_color_2 = QColor(0, 128, 0)
		self.show()
		self.color = 'GREEN'
	
	def turnRed(self):
		self.hide()
		self.on_color_1 = QColor(255, 0, 0)
		self.on_color_2 = QColor(176, 0, 0)
		self.off_color_1 = QColor(28, 0, 0)
		self.off_color_2 = QColor(156, 0, 0)
		self.show()
		self.color = 'RED'
	
	def turnBlue(self):
		self.hide()
		self.on_color_1 = QColor(0, 0, 255)
		self.on_color_2 = QColor(0, 0, 176)
		self.off_color_1 = QColor(0, 0, 28)
		self.off_color_2 = QColor(0, 0, 156)
		self.show()
	
	def turnOn(self):
		self.setChecked(True)
	
	def turnOff(self):
		self.setChecked(False)
	
	def switch(self):
		self.setChecked(not self.isChecked())
	
	def readStatus(self, statString):
		old_status = self.status
		status = statString[8:]
		self.status = status
		
		if self.status != old_status: #COLOR CHANGE
			if status == 'Blocked':
				self.turnRed()
				self.turnOn()
			elif status == 'Ready':
				self.turnGreen()
				self.turnOn()
			elif status == 'Moving':
				self.switch()
			else:
				self.turnBlue() #TODO: enable/disable
		elif status == 'Moving': #BLINKING
			self.switch()
	
	
	
class demoGui(QWidget):
	startSignal = pyqtSignal(int)
	def __init__(self, list_of_axes):
		super().__init__()
		self.list_of_axes = list_of_axes
		self.height = len(list_of_axes)
		self.btnz_A = []
		self.btnz_B = []
		self.btnz_C = []
		self.btnz_S = []
		self.monitorz = []
		self.statz = []
		self.ledz = []
		self.initUI()
		self.show()
	def initUI(self):
		mainLayout = QGridLayout()
		for i, axis in enumerate(self.list_of_axes):
			axis_name = axis.get_name()
			label = QLabel('Axis ' + str(i) + ' : ' + axis_name)
			mainLayout.addWidget(label, i, 0)
			btn_A = QPushButton('<')
			mainLayout.addWidget(btn_A, i, 1)
			self.btnz_A.append(btn_A)
			btn_B = QPushButton('>')
			mainLayout.addWidget(btn_B, i, 2)
			self.btnz_B.append(btn_B)
			btn_C = QPushButton('>>>>')
			mainLayout.addWidget(btn_C, i, 3)
			self.btnz_C.append(btn_C)
			btn_S = QPushButton('STOP')
			mainLayout.addWidget(btn_S, i, 4)
			self.btnz_S.append(btn_S)
			monitor = QLineEdit('0000')
			mainLayout.addWidget(monitor, i, 5)
			self.monitorz.append(monitor)
			statLabel = QLabel('Status: ???')
			self.statz.append(statLabel)
			mainLayout.addWidget(statLabel, i, 6)
			limitIndicator = motorLED(self)
			self.ledz.append(limitIndicator)
			mainLayout.addWidget(limitIndicator, i, 7)
			
			
		self.setLayout(mainLayout)
		self.setWindowTitle('Test GUI for '+ str(motor_type) + ' v.' + str(version))
	def startMeasure(self):
		sender = self.sender()
		j = 0
		for btn in self.btnz_C:
			if btn == sender:
				break
			j += 1
		btn.setEnabled(False)
		self.btnz_A[j].setEnabled(False)
		self.btnz_B[j].setEnabled(False)
		self.startSignal.emit(j)
	
	def stopMeasure(self):
		for j in range(len(self.btnz_A)):
			self.btnz_A[j].setEnabled(True)
			self.btnz_B[j].setEnabled(True)
			self.btnz_C[j].setEnabled(True)
	


def showDemoGui(z):
	gui = demoGui(z)
	return gui

def failLog(axname):
	f = open("log.txt", "a")
	x = datetime.now()
	f.write(str(x) + ' ' + str(axname) + ' FAIL' + '\n')
	f.close()

class demoMoniThread(QThread): #motor position monitor auto-update
	motorPosSignal = pyqtSignal(str)
	statusSignal = pyqtSignal(str)
	def __init__(self, motor):
		QThread.__init__(self)
		self.motor = motor
		self.name = self.motor.get_name()
		self.failed = False
	def __del__(self):
		self.wait()
	def run(self):
		self.running = True
		while self.running:
			mpos = self.motor.get_pos()
			str_mpos = str(mpos)
			self.motorPosSignal.emit(str_mpos)
			time.sleep(0.1)
			if self.motor.is_moving():
				stat_string = 'Status: Moving'
			elif self.motor.is_blocked():
				stat_string = 'Status: Blocked'
				if not self.failed:
					failLog(self.name)
				self.failed = True
			else:
				stat_string = 'Status: Ready'
				if self.failed:
					self.failed = False
			
			self.statusSignal.emit(stat_string)
			


class demoMoveThread(QThread): #simulated experiment-like movement
	finished = pyqtSignal()
	def __init__(self, motor):
		QThread.__init__(self)
		self.motor = motor
	def stop(self):
		self.stopped = True
		self.running = False
	def __del__(self):
		self.wait()
	def run(self):
		self.stopped = False
		self.running = True
		if self.running:
			mpos = self.motor.get_pos()
			for j in range(5):
				if self.running:
					self.motor.start(mpos + (j + 1)*1000)
				else:
					break
				cpos = mpos
				while self.motor.is_moving() and self.running:
					time.sleep(0.5)
					if self.stopped:
						motor.stop()
						self.running = False
				cpos = self.motor.get_pos()
				print('Arrived in position:', cpos)
				time.sleep(2)
		self.finished.emit()
		self.running = False


if __name__ == '__main__':
	app = QApplication(sys.argv)
	
	acsMotors = newACS.newAcsController(newACS.acs_ip, newACS.acs_port, axis_names, contype="ethernet")
	axnum = len(newACS.test_axis_numbers) #number of axes engaged in the demo
	
	'''
	oldMotors = oldStandaDevices()
	axnum = len(oldMotors)
	'''
	
	
	'''
	biba = beepMotor('BIBA')
	boba = beepMotor('BOBA')
	buba = beepMotor('BUBA')
	biba.set_speed(5000)
	buba.set_speed(200)
	
	oldMotors = [biba, boba, buba]
	'''


	
	motors = []
	moniThreads = []
	dmThreads = []
	
	for j in newACS.test_axis_numbers:
		motor = acsMotors.axes[j]
		motors.append(motor)
		mthread = demoMoniThread(motor)
		dt = demoMoveThread(motor)
		moniThreads.append(mthread)
		dmThreads.append(dt)
		mthread.start()
	
	gui = showDemoGui(motors)
	
	#motors[1].set_loft() #NOT WORKING
	
	def startMeasureThread(j):
		dmThreads[j].start()
	
	for j in range(axnum):
		motor = motors[j]
		mthread = moniThreads[j]
		
		dt = dmThreads[j]
		#dt.run()
		
		button_A = gui.btnz_A[j]
		button_B = gui.btnz_B[j]
		button_C = gui.btnz_C[j]
		button_S = gui.btnz_S[j]
		monitor = gui.monitorz[j]
		statLabel = gui.statz[j]
		statLED = gui.ledz[j]
		
		button_A.clicked.connect(motor.test_move_A)
		button_B.clicked.connect(motor.test_move_B)
		button_C.clicked.connect(gui.startMeasure)
		button_S.clicked.connect(motor.stop)
		button_S.clicked.connect(dt.stop)
		
		
		gui.startSignal.connect(startMeasureThread)
		
		
		mthread.motorPosSignal.connect(monitor.setText)
		mthread.statusSignal.connect(statLabel.setText)
		mthread.statusSignal.connect(statLED.readStatus)
		
		dt.finished.connect(gui.stopMeasure)
	

	
	app.exec_()