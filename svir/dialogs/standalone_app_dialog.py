# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 2016-06-29
#        copyright            : (C) 2016 by GEM Foundation
#        email                : devops@openquake.org
# ***************************************************************************/
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.

import json
from qgis.PyQt.QtCore import QUrl, QObject, pyqtSlot, QSettings, Qt
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis
from qgis.gui import QgsMessageBar
from svir.ui.gem_qwebview import GemQWebView
from svir.utilities.shared import DEFAULT_ENGINE_PROFILES


class StandaloneAppDialog(QDialog):
    """
    Dialog to be inherited by OpenQuake standalone applications

    :param app_name: short name of the app as it appears in the url
    :param app_descr: longer name to be used as the window title
    :param gem_header_name: header that identifies that the application is
        being driven from QGIS
    :param gem_header_value: version of the interface between the plugin and
        the embedded application
    :param parent: the parent object (optional)
    """

    def __init__(self, app_name, app_descr, gem_header_name, gem_header_value,
                 parent=None):
        super(StandaloneAppDialog, self).__init__(parent)

        self.message_bar = QgsMessageBar(self)
        self.app_name = app_name
        self.app_descr = app_descr
        self.gem_header_name = gem_header_name
        self.gem_header_value = gem_header_value
        self.web_view = None
        self.set_host()

    def set_host(self):
        engine_profiles = json.loads(QSettings().value(
            'irmt/engine_profiles', DEFAULT_ENGINE_PROFILES))
        cur_eng_profile = QSettings().value('irmt/current_engine_profile')
        if cur_eng_profile is None:
            cur_eng_profile = list(engine_profiles.keys())[0]
        engine_profile = engine_profiles[cur_eng_profile]
        engine_hostname = engine_profile['hostname']
        self.host = QSettings().value('irmt/engine_hostname', engine_hostname)

    def load_homepage(self):
        if self.web_view is not None:
            qurl = QUrl('%s/%s' % (self.host, self.app_name))
            # # Uncomment to use the dummy example instead
            # if self.app_name == 'taxtweb':
            #     qurl = QUrl('http://localhost:8000')
            self.web_view.load(qurl)

    def build_gui(self):
        self.setWindowTitle(self.app_descr)
        self.setWindowIcon(QIcon(":/plugins/irmt/weights.svg"))
        self.vlayout = QVBoxLayout()
        self.setLayout(self.vlayout)
        self.vlayout.addWidget(self.message_bar)
        self.web_view = GemQWebView(self.gem_header_name,
                                    self.gem_header_value,
                                    self.gem_api,
                                    parent=self)
        self.vlayout.addWidget(self.web_view)
        initial_width = 1050
        self.resize(initial_width, self.width())
        self.setWindowFlags(Qt.Window)

        self.reload_homepage_btn = QPushButton("Reload homepage")
        # FIXME: Instead of a fixed width, we should use the natural btn size
        self.reload_homepage_btn.setFixedWidth(150)
        self.reload_homepage_btn.clicked.connect(
                self.on_reload_homepage_btn_clicked)

        self.lower_message_bar = QgsMessageBar(self)

        self.btn_hlayout = QHBoxLayout()
        self.btn_hlayout.setAlignment(Qt.AlignLeft)
        self.btn_hlayout.addWidget(self.reload_homepage_btn)
        self.btn_hlayout.addWidget(self.lower_message_bar)
        self.vlayout.addLayout(self.btn_hlayout)

        self.load_homepage()

    def on_reload_homepage_btn_clicked(self):
        msg = ("Reloading the homepage, all current changes will be discarded."
               " Are you sure?")
        reply = QMessageBox.question(
            self, 'Warning', msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.set_host()
            self.load_homepage()

    def on_set_example_btn_clicked(self):
        qurl = QUrl(self.example_url.text())
        self.web_view.load(qurl)


class CommonApi(QObject):
    """
    Set of shared methods that can be used by all the standalone applications.
    To use one of these methods from javascript, you can do, e.g.:

    gem_api.common.method_name(param)
    """

    def __init__(self, message_bar, parent=None):
        super(CommonApi, self).__init__(parent)
        self.message_bar = message_bar
        self.setObjectName("common")
        # NOTE: to access a property from javascript, a getter has to be
        # implemeimplemented (see method dummy_property_get)
        self.dummy_property = 10

    # return the sum of two integers
    @pyqtSlot(int, int, result=int)
    def add(self, a, b):
        return a + b

    # take a list of strings and return a string
    # because of setapi line above, we get a list of python strings as input
    @pyqtSlot('QStringList', result=str)
    def concat(self, strlist):
        return ''.join(strlist)

    # take a javascript object and return string
    # javascript objects come into python as dictionaries
    # functions are represented by an empty dictionary
    @pyqtSlot('QVariantMap', result=str)
    def json_encode(self, jsobj):
        # import is here to keep it separate from 'required' import
        return json.dumps(jsobj)

    # take a string and return an object (which is represented in python
    # by a dictionary
    @pyqtSlot(str, result='QVariantMap')
    def json_decode(self, jsstr):
        return json.loads(jsstr)

    @pyqtSlot()
    def notify_click(self):
        self.info("Clicked!")

    @pyqtSlot(str)
    def info(self, message):
        self.message_bar.pushMessage(message, level=Qgis.Info)

    @pyqtSlot(str)
    def warning(self, message):
        self.message_bar.pushMessage(message, level=Qgis.Warning)

    @pyqtSlot(str)
    def error(self, message):
        self.message_bar.pushMessage(message, level=Qgis.Critical)

    @pyqtSlot(result=int)
    def dummy_property_get(self):
        "A getter must be defined to access instance properties"
        return self.dummy_property


class GemApi(QObject):
    def __init__(self, message_bar, parent=None):
        super(GemApi, self).__init__(parent)
        self.common = CommonApi(message_bar, self)
