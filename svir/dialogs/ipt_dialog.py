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

from qgis.PyQt.QtGui import QPushButton, QLineEdit, QHBoxLayout
from qgis.PyQt.QtCore import QUrl, pyqtSlot
from qgis.PyQt.QtNetwork import QNetworkRequest, QHttpMultiPart, QHttpPart
from svir.dialogs.standalone_app_dialog import StandaloneAppDialog, GemApi
from svir.utilities.shared import DEBUG


class IptDialog(StandaloneAppDialog):
    """
    Dialog that embeds the OpenQuake Input Modelling Toolkit
    standalone application
    """

    def __init__(self, parent=None):
        app_name = 'ipt'
        app_descr = 'OpenQuake Input Preparation Toolkit'
        gem_header_name = "Gem--Qgis-Oq-Irmt--Ipt"
        gem_header_value = "0.1.0"
        super(IptDialog, self).__init__(
            app_name, app_descr, gem_header_name, gem_header_value, parent)
        self.gem_api = IptPythonApi(self.message_bar, self)
        self.build_gui()

    def build_gui(self):
        super(IptDialog, self).build_gui()
        if DEBUG:
            self.set_example_btn = QPushButton("Set example")
            self.set_example_btn.clicked.connect(
                self.on_set_example_btn_clicked)
            ipt_example = '%s/%s?tab_id=1&subtab_id=0&example_id=99' % (
                self.host, self.app_name)
            self.example_url = QLineEdit(ipt_example)
            self.hlayout = QHBoxLayout()
            self.hlayout.addWidget(self.example_url)
            self.hlayout.addWidget(self.set_example_btn)
            self.vlayout.addLayout(self.hlayout)

    def on_set_example_btn_clicked(self):
        qurl = QUrl(self.example_url.text())
        self.web_view.load(qurl)


class IptPythonApi(GemApi):
    """
    API methods that are specific for the IPT application
    (other shared methods are defined in the CommonApi)
    """

    # javascript objects come into python as dictionaries
    @pyqtSlot(str, str, 'QVariantList', 'QVariantList')
    def delegate_download(self, action_url, method, headers, data):
        """
        :param action_url: url to call on ipt api
        :param method: string like 'POST'
        :param headers: list of strings
        :param data: list of dictionaries {name (string) value(string)}
        """
        # TODO: Accept also methods other than POST
        assert method == 'POST', method
        if ':' in action_url:
            qurl = QUrl(action_url)
        elif action_url.startswith('/'):
            qurl = QUrl("%s%s" % (self.parent().host, action_url))
        else:
            qurl = QUrl(
                "%s/%s" %
                ('/'.join(self.parent().web_view.url().split('/')[:-1]),
                 action_url))
        manager = self.parent().web_view.page().networkAccessManager()
        request = QNetworkRequest(qurl)
        for header in headers:
            request.setRawHeader(header['name'], header['value'])
        multipart = QHttpMultiPart(QHttpMultiPart.FormDataType)
        for d in data:
            part = QHttpPart()
            part.setHeader(QNetworkRequest.ContentDispositionHeader,
                           "form-data; name=\"%s\"" % d['name'])
            part.setBody(d['value'])
            multipart.append(part)
        manager.post(request, multipart)
