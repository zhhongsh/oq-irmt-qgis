# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_input_tool_window.ui'
#
# Created: Wed Aug  7 17:06:09 2013
#      by: PyQt4 UI code generator 4.9.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_InputToolWindow(object):
    def setupUi(self, InputToolWindow):
        InputToolWindow.setObjectName(_fromUtf8("InputToolWindow"))
        InputToolWindow.resize(1011, 830)
        self.centralwidget = QtGui.QWidget(InputToolWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.tabwidget = QtGui.QTabWidget(self.centralwidget)
        self.tabwidget.setObjectName(_fromUtf8("tabwidget"))
        self.exposure = QtGui.QWidget()
        self.exposure.setObjectName(_fromUtf8("exposure"))
        self.tabwidget.addTab(self.exposure, _fromUtf8(""))
        self.vulnerability = QtGui.QWidget()
        self.vulnerability.setMinimumSize(QtCore.QSize(947, 718))
        self.vulnerability.setObjectName(_fromUtf8("vulnerability"))
        self.verticalLayout = QtGui.QVBoxLayout(self.vulnerability)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.vSetsTbl = QtGui.QTableWidget(self.vulnerability)
        self.vSetsTbl.setObjectName(_fromUtf8("vSetsTbl"))
        self.vSetsTbl.setColumnCount(4)
        self.vSetsTbl.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.vSetsTbl.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.vSetsTbl.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.vSetsTbl.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        self.vSetsTbl.setHorizontalHeaderItem(3, item)
        self.verticalLayout.addWidget(self.vSetsTbl)
        self.imtTbl = QtGui.QTableWidget(self.vulnerability)
        self.imtTbl.setObjectName(_fromUtf8("imtTbl"))
        self.imtTbl.setColumnCount(0)
        self.imtTbl.setRowCount(1)
        item = QtGui.QTableWidgetItem()
        self.imtTbl.setVerticalHeaderItem(0, item)
        self.verticalLayout.addWidget(self.imtTbl)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.vFnTbl = QtGui.QTableWidget(self.vulnerability)
        self.vFnTbl.setObjectName(_fromUtf8("vFnTbl"))
        self.vFnTbl.setColumnCount(3)
        self.vFnTbl.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.vFnTbl.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.vFnTbl.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.vFnTbl.setHorizontalHeaderItem(2, item)
        self.horizontalLayout.addWidget(self.vFnTbl)
        self.imlsTbl = QtGui.QTableWidget(self.vulnerability)
        self.imlsTbl.setObjectName(_fromUtf8("imlsTbl"))
        self.imlsTbl.setColumnCount(3)
        self.imlsTbl.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.imlsTbl.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.imlsTbl.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.imlsTbl.setHorizontalHeaderItem(2, item)
        self.horizontalLayout.addWidget(self.imlsTbl)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.tabwidget.addTab(self.vulnerability, _fromUtf8(""))
        self.fragility = QtGui.QWidget()
        self.fragility.setObjectName(_fromUtf8("fragility"))
        self.tabwidget.addTab(self.fragility, _fromUtf8(""))
        self.sitemodel = QtGui.QWidget()
        self.sitemodel.setObjectName(_fromUtf8("sitemodel"))
        self.tabwidget.addTab(self.sitemodel, _fromUtf8(""))
        self.rupturemodel = QtGui.QWidget()
        self.rupturemodel.setObjectName(_fromUtf8("rupturemodel"))
        self.tabwidget.addTab(self.rupturemodel, _fromUtf8(""))
        self.config = QtGui.QWidget()
        self.config.setObjectName(_fromUtf8("config"))
        self.tabwidget.addTab(self.config, _fromUtf8(""))
        self.gridLayout.addWidget(self.tabwidget, 0, 0, 1, 1)
        InputToolWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(InputToolWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1011, 25))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        InputToolWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(InputToolWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        InputToolWindow.setStatusBar(self.statusbar)
        self.toolBar = QtGui.QToolBar(InputToolWindow)
        self.toolBar.setObjectName(_fromUtf8("toolBar"))
        InputToolWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)

        self.retranslateUi(InputToolWindow)
        self.tabwidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(InputToolWindow)

    def retranslateUi(self, InputToolWindow):
        InputToolWindow.setWindowTitle(QtGui.QApplication.translate("InputToolWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.tabwidget.setTabText(self.tabwidget.indexOf(self.exposure), QtGui.QApplication.translate("InputToolWindow", "Exposure Model", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vSetsTbl.horizontalHeaderItem(0)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Set ID", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vSetsTbl.horizontalHeaderItem(1)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Asset Category", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vSetsTbl.horizontalHeaderItem(2)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "New Column", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vSetsTbl.horizontalHeaderItem(3)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "IMT", None, QtGui.QApplication.UnicodeUTF8))
        item = self.imtTbl.verticalHeaderItem(0)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "IMT", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vFnTbl.horizontalHeaderItem(0)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Fn ID", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vFnTbl.horizontalHeaderItem(1)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Prob Dist", None, QtGui.QApplication.UnicodeUTF8))
        item = self.vFnTbl.horizontalHeaderItem(2)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Category", None, QtGui.QApplication.UnicodeUTF8))
        item = self.imlsTbl.horizontalHeaderItem(0)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "IML", None, QtGui.QApplication.UnicodeUTF8))
        item = self.imlsTbl.horizontalHeaderItem(1)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Loss Ratio", None, QtGui.QApplication.UnicodeUTF8))
        item = self.imlsTbl.horizontalHeaderItem(2)
        item.setText(QtGui.QApplication.translate("InputToolWindow", "Coeff Variation", None, QtGui.QApplication.UnicodeUTF8))
        self.tabwidget.setTabText(self.tabwidget.indexOf(self.vulnerability), QtGui.QApplication.translate("InputToolWindow", "Vulnerability Functions", None, QtGui.QApplication.UnicodeUTF8))
        self.tabwidget.setTabText(self.tabwidget.indexOf(self.fragility), QtGui.QApplication.translate("InputToolWindow", "Fragility Functions", None, QtGui.QApplication.UnicodeUTF8))
        self.tabwidget.setTabText(self.tabwidget.indexOf(self.sitemodel), QtGui.QApplication.translate("InputToolWindow", "Site Model", None, QtGui.QApplication.UnicodeUTF8))
        self.tabwidget.setTabText(self.tabwidget.indexOf(self.rupturemodel), QtGui.QApplication.translate("InputToolWindow", "Rupture Model", None, QtGui.QApplication.UnicodeUTF8))
        self.tabwidget.setTabText(self.tabwidget.indexOf(self.config), QtGui.QApplication.translate("InputToolWindow", "Config File", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBar.setWindowTitle(QtGui.QApplication.translate("InputToolWindow", "toolBar", None, QtGui.QApplication.UnicodeUTF8))

