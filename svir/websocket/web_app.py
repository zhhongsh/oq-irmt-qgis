# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 2016-06-29
#        copyright            : (C) 2018 by GEM Foundation
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

from uuid import uuid4
from qgis.PyQt.QtCore import QObject
from qgis.core import Qgis
from svir.utilities.utils import log_msg


class WebApp(QObject):

    def __init__(self, app_name, wss, message_bar, parent=None):
        assert app_name is not None
        super().__init__(parent)
        self.wss = wss  # thread running the websocket server
        self.message_bar = message_bar
        self.app_name = app_name
        self.allowed_meths = [
            'window_open', 'ext_app_open', 'set_cells']
        self.pending = {}

    def run_command(self, command, args=()):
        # called when IRMT wants to send a command to the websocket
        if command not in self.allowed_meths:
            return 'Method "%s" not allowed' % command
        uuid = uuid4().urn[9:]
        api_msg = {
            'uuid': uuid,
            'msg': {
                'command': command,
                'args': args
            }
        }
        self.send(api_msg)
        self.pending[uuid] = api_msg

    def receive(self, api_msg):
        # it happens when the websocket receives a message
        api_uuid = api_msg['uuid']
        if 'reply' in api_msg:
            app_msg = api_msg['reply']
            uuid = api_msg['uuid']
            if uuid in self.pending:
                print("Command pending found [%s]" % uuid)
                # FIXME: call CB
                if ('complete' not in app_msg or
                        app_msg['complete'] is True):
                    print("Command pending deleted [%s]" % uuid)
                    del self.pending[uuid]
            return
        else:
            app_msg = api_msg['msg']
            command = app_msg['command']
            if command not in self.allowed_meths:
                api_reply = {
                    'uuid': api_uuid,
                    'reply': {
                        'success': False,
                        'msg': 'Method "%s" not allowed' % command
                    }
                }
                self.send(api_reply)
                return

            args = app_msg['args']
            meth = getattr(self, command)

            # FIXME: manage command exception
            ret = meth(*args, api_uuid=api_uuid)

            api_reply = {'uuid': api_uuid, 'reply': ret}
            self.send(api_reply)

    def send(self, api_msg):
        # it sends a message to the websocket
        hyb_msg = {'app': self.app_name, 'msg': api_msg}
        self.wss.irmt_thread.send_to_wss_sig.emit(hyb_msg)

    # Deprecated
    def ext_app_open(self, content, api_uuid=None):
        # FIXME: the name is misleading. This method just prints in the message
        # bar a string specified in the first arg
        msg = "%s ext_app_open: %s" % (self.app_name, content)
        log_msg(msg, message_bar=self.message_bar)
        return {'success': True}

    # FIXME: adapt the following to the new websocket approach

    # # take a javascript object and return string
    # # javascript objects come into python as dictionaries
    # # functions are represented by an empty dictionary
    # @pyqtSlot('QVariantMap', result=str)
    # def json_encode(self, jsobj):
    #     # import is here to keep it separate from 'required' import
    #     return json.dumps(jsobj)

    # # take a string and return an object (which is represented in python
    # # by a dictionary
    # @pyqtSlot(str, result='QVariantMap')
    # def json_decode(self, jsstr):
    #     return json.loads(jsstr)

    def notify_click(self, api_uuid=None):
        self.info("Clicked!")
        return {'success': True}

    def info(self, message, api_uuid=None):
        self.message_bar.pushMessage(message, level=Qgis.Info)
        return {'success': True}

    def warning(self, message, api_uuid=None):
        self.message_bar.pushMessage(message, level=Qgis.Warning)
        return {'success': True}

    def error(self, message, api_uuid=None):
        self.message_bar.pushMessage(message, level=Qgis.Critical)
        return {'success': True}

    # @pyqtSlot(result=int)
    # def dummy_property_get(self):
    #     "A getter must be defined to access instance properties"
    #     return self.dummy_property
