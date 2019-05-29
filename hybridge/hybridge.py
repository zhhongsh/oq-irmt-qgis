# -*- coding: utf-8 -*-
# /***************************************************************************
# HyBridge
#                                 A QGIS plugin
# OpenQuake Hybridge
#                              -------------------
#        begin                : 2013-10-24
#        copyright            : (C) 2013-2017 by GEM Foundation
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

import os.path
import random
import inspect
import qgis

from qgis.PyQt.QtCore import (
    QCoreApplication, QObject, QSettings, QTranslator, qVersion, pyqtSlot,
    )
from hybridge.websocket.simple_websocket_server import SimpleWebSocketServer
from hybridge.utilities.utils import log_msg

# DO NOT REMOVE THIS
# noinspection PyUnresolvedReferences
import hybridge.resources_rc  # pylint: disable=unused-import  # NOQA


class HyBridge(QObject):

    __instance = None
    __is_initialized = False

    def __new__(cls, iface=None):
        # when QGIS instantiates this, it passes iface as argument,
        # but when you get the instance afterwards you don't need to pass it
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.iface = None
            cls.__instance.canvas = None
        return cls.__instance

    def __init__(self, iface=None):
        if iface is not None:
            # Save reference to the QGIS interface
            self.iface = iface
            self.canvas = self.iface.mapCanvas()
        if self.__is_initialized:
            return
        super().__init__()
        random.seed()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n',
                                   'hybridge_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.websocket_thread = None
        self.plugins = {}
        self.__class__.__is_initialized = True

    def initGui(self):
        print("Initializing HyBridge")

    def unload(self):
        # shutdown websocket server
        self.stop_websocket()

    @staticmethod
    def get_websocket_thread(caller, iface=None):
        instance = HyBridge(iface=iface)
        # FIXME: this works if only one plugin is using hybridge!
        #        We should allow N callers
        instance.caller = caller
        instance.start_websocket()
        return instance.websocket_thread

    @pyqtSlot('QVariantMap')
    def handle_wss_error_sig(self, data):
        log_msg("wss_error_sig: %s" % data, level='C',
                message_bar=self.iface.messageBar())

    @pyqtSlot('QVariantMap', int)
    def handle_from_socket_received_old(self, hyb_msg, ws_uuid):
        log_msg("handle_from_socket_received: %s" % hyb_msg)

        app_name = hyb_msg['app']
        api_msg = hyb_msg['msg']
        # NOTE: this assumes the caller plugin has a defined list of web_apis
        app = self.caller.web_apis[app_name]

        app.receive(api_msg)

    @pyqtSlot('QVariantMap', 'QVariantMap')
    def handle_from_socket_received(self, hyb_msg, ws_info):
        log_msg("handle_from_socket_received: %s" % hyb_msg)

        app_name = hyb_msg['app']
        api_msg = hyb_msg['msg']
        # NOTE: this assumes the caller plugin has a defined list of web_apis
        apis = self.plugins[ws_info['pin_name']]['apis']
        api = apis[ws_info['api_name']]
        api.receive(api_msg)

    @pyqtSlot('QVariantMap')
    def handle_from_socket_sent(self, data):
        log_msg("from_socket_sent: %s" % data)

    @pyqtSlot('QVariantMap')
    def handle_open_connection_sig(self, ws_info):
        print('handle_open_connection_sig')
        apis = self.plugins[ws_info['pin_name']]['apis']
        api = apis[ws_info['api_name']]
        print(api)

        # MN FIXME: turn api button to "connected"

        # NOTE: this assumes the caller plugin has lists of webapi_action_names
        # and registered_actions
        # for action_name in self.caller.webapi_action_names:
        #     self.caller.registered_actions[action_name].setEnabled(True)

        # for web_api_name in self.caller.web_apis:
        #     web_api = self.caller.web_apis[web_api_name]
        #     web_api.apptrack_status()

    @pyqtSlot()
    def handle_close_connection_sig(self):
        print('\nhandle_close_connection_sig')
        # NOTE: this assumes the caller plugin has lists of webapi_action_names
        # and registered_actions
        for web_api_name in self.caller.web_apis:
            web_api = self.caller.web_apis[web_api_name]
            web_api.apptrack_status_cleanup()

        for action_name in self.caller.webapi_action_names:
            # FIXME: set the icon without the green dot
            self.caller.registered_actions[action_name].setEnabled(False)

    def start_websocket(self):
        if self.websocket_thread is not None:
            return
        host = 'localhost'
        port = 8040
        self.websocket_thread = SimpleWebSocketServer(host, port, self.caller)
        self.websocket_thread.wss_error_sig['QVariantMap'].connect(
            self.handle_wss_error_sig)
        self.websocket_thread.from_socket_received[
            'QVariantMap', 'QVariantMap'].connect(
            self.handle_from_socket_received)
        self.websocket_thread.from_socket_sent['QVariantMap'].connect(
            self.handle_from_socket_sent)
        self.websocket_thread.open_connection_sig['QVariantMap'].connect(
            self.handle_open_connection_sig)
        self.websocket_thread.close_connection_sig.connect(
            self.handle_close_connection_sig)
        self.websocket_thread.start()
        log_msg("Web socket server started",
                message_bar=self.iface.messageBar())

    def stop_websocket(self):
        if self.websocket_thread is not None:
            self.websocket_thread.stop_running()
            if self.websocket_thread.wait(5000):
                log_msg("Web socket server stopped",
                        message_bar=self.iface.messageBar())
            else:  # timed out before finishing execution
                self.websocket_thread.terminate()
                log_msg("Web socket server stopped with force",
                        level='W', message_bar=self.iface.messageBar())
            self.websocket_thread.exit()
            self.websocket_thread = None

    def plugin_register(self, plugin, apis):
        plugin_prefix = None
        plugin_filepath = inspect.stack()[1].filename
        for ppath in qgis.utils.plugin_paths:
            print("ppath: %s" % ppath)
            if plugin_filepath.startswith(ppath):
                plugin_prefix = plugin_filepath[len(ppath):]
                print("plugin_prefix1: %s" % plugin_prefix)
                plugin_prefix = plugin_prefix.split(os.sep)[1]
                print("plugin_prefix2: %s" % plugin_prefix)
                break
        else:
            raise ValueError('%s not found' % plugin_filepath)
        self.plugins[plugin_prefix] = {
            'name': plugin_prefix, 'plugin': plugin, 'apis': apis}
        # for api in apis.values():
        #     self.websocket_thread.register_caller(api)