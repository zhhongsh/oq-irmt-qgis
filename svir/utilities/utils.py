# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 2013-10-24
#        copyright            : (C) 2013-2015 by GEM Foundation
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

import numpy
import collections
import json
import os
import sys
import locale
from copy import deepcopy
from time import time
from pprint import pformat
from qgis.core import (QgsMapLayerRegistry,
                       QgsProject,
                       QgsMessageLog,
                       QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsGraduatedSymbolRendererV2,
                       QGis,
                       )
from qgis.gui import QgsMessageBar

from PyQt4 import uic
from PyQt4.QtCore import Qt, QSettings, QUrl
from PyQt4.QtGui import (QApplication,
                         QProgressBar,
                         QToolButton,
                         QFileDialog,
                         QMessageBox,
                         QColor)

from svir.third_party.poster.encode import multipart_encode
from svir.utilities.shared import DEBUG

F32 = numpy.float32

_IRMT_VERSION = None


def get_irmt_version():
    """
    Get the plugin's version from metadata.txt
    """
    global _IRMT_VERSION
    if _IRMT_VERSION is None:
        metadata_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'metadata.txt')
        with open(metadata_path, 'r') as f:
            for line in f:
                if line.startswith('version='):
                    _IRMT_VERSION = line.split('=')[1].strip()
    return _IRMT_VERSION


def get_qgis_version():
    qgis_version_str = QGis.QGIS_VERSION
    qgis_version = tuple(map(int, qgis_version_str.split('.')))
    return qgis_version


def log_msg(message, tag='GEM IRMT Plugin', level='I', message_bar=None,
            duration=None):
    """
    Add a message to the QGIS message log. If a messageBar is provided,
    the same message will be displayed also in the messageBar. In the latter
    case, warnings and critical messages will have no timeout, whereas
    info messages will have a duration of 5 seconds.

    :param message: the message
    :param tag: the log topic
    :param level:
        the importance level
        'I' -> QgsMessageLog.INFO,
        'W' -> QgsMessageLog.WARNING,
        'C' -> QgsMessageLog.CRITICAL
    :param message_bar: a `QgsMessageBar` instance
    :param duration: how long (in seconds) the message will be displayed (use 0
                     to keep the message visible indefinitely, or None to use
                     the default duration of the chosen level
    """
    levels = {'I': {'log': QgsMessageLog.INFO,
                    'bar': QgsMessageBar.INFO},
              'W': {'log': QgsMessageLog.WARNING,
                    'bar': QgsMessageBar.WARNING},
              'C': {'log': QgsMessageLog.CRITICAL,
                    'bar': QgsMessageBar.CRITICAL}}
    if level not in levels:
        raise ValueError('Level must be one of %s' % levels.keys())

    # if we are running nosetests, exit on critical errors
    if 'nose' in sys.modules and level == 'C':
        raise RuntimeError(message)
    else:
        QgsMessageLog.logMessage(tr(message), tr(tag), levels[level]['log'])
        if message_bar is not None:
            if level == 'I':
                title = 'Info'
                duration = duration if duration is not None else 8
            elif level == 'W':
                title = 'Warning'
                duration = duration if duration is not None else 0
            elif level == 'C':
                title = 'Error'
                duration = duration if duration is not None else 0
            message_bar.pushMessage(tr(title),
                                    tr(message),
                                    levels[level]['bar'],
                                    duration)


def tr(message):
    """
    Leverage QApplication.translate to translate a message

    :param message: the message to be translated
    :returns: the return value of `QApplication.translate('Irmt', message)`
    """
    return QApplication.translate('Irmt', message)


def confirmation_on_close(parent, event=None):
    """
    Open a QMessageBox to confirm closing a dialog discarding changes

    :param parent: the parent dialog that is being closed
    :param event: event that triggered this dialog (e.g. reject or closeEvent)
    """
    msg = tr("WARNING: all unsaved changes will be lost. Are you sure?")
    reply = QMessageBox.question(
        parent, 'Message', msg, QMessageBox.Yes, QMessageBox.No)
    if event is not None:
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
    else:
        if reply == QMessageBox.Yes:
            parent.__class__.__base__.reject(parent)


def replace_fields(sub_tree_root, before, after):
    """
    Recursively search the project definition for 'field's equal to the
    string before and replace the value with the string after.
    It is useful, e.g., when we transform a field that is tracked by the
    project definition, and we obtain a new field that we want to track
    instead of the original one.
    It works by side-effect, modifying the passed project definition.

    :param sub_tree_root:
        node of a project definition. From that node (used as root) towards the
        leaves of the tree, the function will recursively search for nodes with
        a 'field' property that contains the string before
    :param before: string to be replaced
    :param after: new value for the replaced string
    """
    if 'field' in sub_tree_root and sub_tree_root['field'] == before:
        sub_tree_root['field'] = after
    if 'children' in sub_tree_root:
        for child in sub_tree_root['children']:
            replace_fields(child, before, after)


def count_heading_commented_lines(fname):
    """
    count top lines in the file starting with '#'
    """
    with open(fname) as f:
        lines_to_skip_count = 0
        for line in f:
            li = line.strip()
            if li.startswith('#'):
                lines_to_skip_count += 1
            else:
                break
    if DEBUG:
        log_msg("The file contains %s heading lines starting with #" % (
            lines_to_skip_count))
    return lines_to_skip_count


def set_operator(sub_tree, operator):
    """
    if the root of the sub_tree has children, set the operator to be used to
    combine the children. If any of the children have children, set also
    their operators to the same one applied to the root.

    :param sub_tree: root of the subtree to which we want to set the operator
    :param operator: the operator to be applied
    :returns: the modified subtree
    """
    node = deepcopy(sub_tree)
    if 'children' in node:
        for child_idx, child in enumerate(node['children']):
            modified_child = set_operator(child, operator)
            node['children'][child_idx] = modified_child
        node['operator'] = operator
    return node


def get_node(sub_tree, name):
    """
    Browse the tree (recursively searching each node's children), looking for
    a node with a specific name.

    :param sub_tree: root of the subtree through which we want to search
    :param name: name of the node to be searched
    :returns: the node, if found, otherwise None
    """
    if 'name' in sub_tree and sub_tree['name'] == name:
        found_node = sub_tree
        return found_node
    if 'children' in sub_tree:
        for child in sub_tree['children']:
            found_node = get_node(child, name)
            if found_node:
                return found_node
    return None  # not found


def get_field_names(sub_tree, field_names=None):
    """
    Return a list of all the field names defined in the project definition

    :sub_tree: root of the subtree for which we want to collect field names
    :param field_names: an accumulator that is extended browsing the tree
                        recursively (if None, a list will be created) and
                        collecting the field names
    :returns: the accumulator
    """
    if field_names is None:
        field_names = set()
    if 'field' in sub_tree:
        field_names.add(sub_tree['field'])
    if 'children' in sub_tree:
        for child in sub_tree['children']:
            child_field_names = get_field_names(child, field_names)
            field_names = field_names.union(child_field_names)
    return field_names


def clear_progress_message_bar(msg_bar, msg_bar_item=None):
    """
    Clear the progress messsage bar
    """
    if msg_bar_item:
        msg_bar.popWidget(msg_bar_item)
    else:
        msg_bar.clearWidgets()


def create_progress_message_bar(msg_bar, msg, no_percentage=False):
    """
    Use the messageBar of QGIS to display a message describing what's going
    on (typically during a time-consuming task), and a bar showing the
    progress of the process.

    :param msg: Message to be displayed, describing the current task
    :type: str

    :returns: progress object on which we can set the percentage of
              completion of the task through progress.setValue(percentage)
    :rtype: QProgressBar
    """
    progress_message_bar = msg_bar.createMessage(msg)
    progress = QProgressBar()
    if no_percentage:
        progress.setRange(0, 0)
    progress_message_bar.layout().addWidget(progress)
    msg_bar.pushWidget(progress_message_bar, msg_bar.INFO)
    return progress_message_bar, progress


def assign_default_weights(svi_themes):
    """
    Count themes and indicators and assign default weights
    using 2 decimal points (%.2f)

    :param svi_themes: list of nodes corresponding to socioeconomic themes
    """
    themes_count = len(svi_themes)
    theme_weight = float('%.2f' % (1.0 / themes_count))
    for i, theme in enumerate(svi_themes):
        theme['weight'] = theme_weight
        for indicator in theme['children']:
            indicator_weight = 1.0 / len(theme['children'])
            indicator_weight = '%.2f' % indicator_weight
            indicator['weight'] = float(indicator_weight)


def reload_layers_in_cbx(combo, layer_types=None, skip_layer_ids=None):
    """
    Load layers into a combobox. Can filter by layer type.
    the additional filter can be QgsMapLayer.VectorLayer, ...

    :param combo: The combobox to be repopulated
    :type combo: QComboBox
    :param layer_types: list containing types or None if all type accepted
    :type layer_types: [QgsMapLayer.LayerType, ...]
    :param skip_layer_ids: list containing layers to be skipped in the combobox
     or None if all layers accepted
    :type skip_layer_ids: [QgsMapLayer ...]
    """
    combo.clear()
    for l in QgsMapLayerRegistry.instance().mapLayers().values():
        layer_type_allowed = bool(layer_types is None
                                  or l.type() in layer_types)
        layer_id_allowed = bool(skip_layer_ids is None
                                or l.id() not in skip_layer_ids)
        if layer_type_allowed and layer_id_allowed:
            combo.addItem(l.name(), l)


def reload_attrib_cbx(
        combo, layer, prepend_empty_item=False, *valid_field_types):
    """
    Load attributes of a layer into a combobox. Can filter by field data type.
    the optional filter can be NUMERIC_FIELD_TYPES, TEXTUAL_FIELD_TYPES, ...
    if no filter is specified all fields are returned

    :param combo: The combobox to be repopulated
    :type combo: QComboBox
    :param layer: The QgsVectorLayer from where the fields are read
    :type layer: QgsVectorLayer
    :param prepend_empty_item: if to prepend an empty item to the combo
    :type layer: Bool
    :param \*valid_field_types: multiple tuples containing types
    :type \*valid_field_types: tuple, tuple, ...
    """
    field_types = set()
    for field_type in valid_field_types:
        field_types.update(field_type)

    # reset combo box
    combo.clear()
    # populate combo box with field names taken by layers
    fields = list(layer.fields())

    if prepend_empty_item:
        combo.addItem(None)

    for field in fields:
        # add if in field_types
        if not field_types or field.typeName() in field_types:
            combo.addItem(field.name(), field)


def toggle_select_features(layer, use_new, new_feature_ids, old_feature_ids):
    """
    Toggles feature selection between two sets.

    :param layer: The QgsVectorLayer where the selection is applied
    :type layer: QgsVectorLayer
    :param use_new: which list to select
    :type use_new: bool
    :param new_feature_ids: The list to select if use_new is true
    :type new_feature_ids: QgsFeatureIds
    :param old_feature_ids: The list to select if use_new is false
    :type old_feature_ids: QgsFeatureIds
    """
    if use_new:
        layer.setSelectedFeatures(list(new_feature_ids))
    else:
        layer.setSelectedFeatures(list(old_feature_ids))


def toggle_select_features_widget(title, text, button_text, layer,
                                  new_feature_ids, old_feature_ids):
    """
    Create a widget for QgsMessageBar to switch between two sets.

    :param title: The title
    :type title: str
    :param text: The text message
    :type text: str
    :param button_text: The text on the toggle button
    :type button_text: str
    :param layer: The QgsVectorLayer where the selection is applied
    :type layer: QgsVectorLayer
    :param new_feature_ids: The list to select if use_new is true
    :type new_feature_ids: QgsFeatureIds
    :param old_feature_ids: The list to select if use_new is false
    :type old_feature_ids: QgsFeatureIds

    :returns: the widget
    """
    widget = QgsMessageBar.createMessage(title, text)
    button = QToolButton(widget)
    button.setCheckable(True)
    button.setText(button_text)
    button.toggled.connect(
        lambda on,
        layer=layer,
        new_feature_ids=new_feature_ids,
        old_feature_ids=old_feature_ids:
        toggle_select_features(layer,
                               on,
                               new_feature_ids,
                               old_feature_ids))
    widget.layout().addWidget(button)
    return widget


def platform_login(host, username, password, session):
    """
    Logs in a session to a platform

    :param host: The host url
    :type host: str
    :param username: The username
    :type username: str
    :param password: The password
    :type password: str
    :param session: The session to be autenticated
    :type session: Session
    """

    login_url = host + '/account/ajax_login'
    session_resp = session.post(login_url,
                                data={
                                    "username": username,
                                    "password": password
                                },
                                timeout=10,
                                )
    if session_resp.status_code != 200:  # 200 means successful:OK
        error_message = ('Unable to get session for login: %s' %
                         session_resp.text)
        raise SvNetworkError(error_message)


def engine_login(host, username, password, session):
    """
    Logs in a session to a engine server

    :param host: The host url
    :type host: str
    :param username: The username
    :type username: str
    :param password: The password
    :type password: str
    :param session: The session to be autenticated
    :type session: Session
    """

    login_url = host + '/accounts/ajax_login/'
    session_resp = session.post(login_url,
                                data={
                                    "username": username,
                                    "password": password
                                },
                                timeout=10,
                                )
    if session_resp.status_code != 200:  # 200 means successful:OK
        error_message = ('Unable to get session for login: %s' %
                         session_resp.text)
        raise SvNetworkError(error_message)


def update_platform_project(host,
                            session,
                            project_definition,
                            platform_layer_id):
    """
    Add a project definition to one of the available projects on the
    OpenQuake Platform

    :param host: url of the OpenQuake Platform server
    :param session: authenticated session to be used
    :param project_definition: the project definition to be added
    :param platform_layer_id: the id of the platform layer to be updated

    :returns: the server's response
    """
    proj_def_str = json.dumps(project_definition,
                              sort_keys=False,
                              indent=2,
                              separators=(',', ': '))
    payload = {'layer_name': platform_layer_id,
               'project_definition': proj_def_str}
    resp = session.post(host + '/svir/add_project_definition', data=payload)
    return resp


def ask_for_destination_full_path_name(
        parent, text='Save File', filter='Shapefiles (*.shp)'):
    """
    Open a dialog to ask for a destination full path name, initially pointing
    to the home directory.
    QFileDialog by defaults asks for confirmation if an existing file is
    selected and it automatically resolves symlinks.

    :param parent: the parent dialog
    :param text: the dialog's title text
    :param filter:
        filter files by specific formats. Default: 'Shapefiles (\*.shp)'
        A more elaborate example:

        "Images (\*.png \*.xpm \*.jpg);;
        Text files (\*.txt);;XML files (\*.xml)"

    :returns: full path name of the destination file
    """
    return QFileDialog.getSaveFileName(
        parent, text, directory=os.path.expanduser("~"), filter=filter)


def ask_for_download_destination_folder(parent, text='Download destination'):
    """
    Open a dialog to ask for a download destination folder, initially pointing
    to the home directory.

    :param parent: the parent dialog
    :param text: the dialog's title text

    :returns: full path of the destination folder
    """
    return QFileDialog.getExistingDirectory(
        parent,
        text,
        os.path.expanduser("~"))


def files_exist_in_destination(destination, file_names):
    """
    Check if any of the provided file names exist in the destination folder

    :param destination: destination folder
    :param file_names: list of file names

    :returns: list of file names that already exist in the destination folder
    """
    existing_files_in_destination = []
    for file_name in file_names:
        file_path = os.path.join(destination, file_name)
        if os.path.isfile(file_path):
            existing_files_in_destination.append(file_path)
    return existing_files_in_destination


def confirm_overwrite(parent, files):
    """
    Open a dialog to ask for user's confirmation on file overwriting
    """
    return QMessageBox.question(
        parent,
        'Overwrite existing files?',
        'If you continue the following files will be '
        'overwritten: %s\n\n'
        'Continue?' % '\n'.join(files),
        QMessageBox.Yes | QMessageBox.No)


class Register(collections.OrderedDict):
    """
    Useful to keep (in a single point) a register of available variants of
    something, e.g. a set of different transformation algorithms
    """
    def add(self, tag):
        """
        Add a new variant to the OrderedDict
        For instance, if we add a class implementing a specific transformation
        algorithm, the register will keep track of a new item having as key the
        name of the algorithm and as value the class implementing the algorithm
        """
        def dec(obj):
            self[tag] = obj
            return obj
        return dec


class TraceTimeManager(object):
    """
    Wrapper to check how much time is needed to complete a block of code

    :param message: message describing the task to be monitored
    :param debug: if False, nothing will be done. Otherwise, times will be
                  measured and logged
    """
    def __init__(self, message, debug=False):
        self.debug = debug
        self.message = message
        self.t_start = None
        self.t_stop = None

    def __enter__(self):
        if self.debug:
            log_msg(self.message)
            self.t_start = time()

    def __exit__(self, type, value, traceback):
        if self.debug:
            self.t_stop = time()
            log_msg("Completed in %f" % (self.t_stop - self.t_start))


class LayerEditingManager(object):
    """
    Wrapper to be used to edit a layer,
    that executes startEditing and commitChanges

    :param layer: the layer that is being edited
    :param message: description of the task that is being performed
    :param debug: if False, nothing will be logged
    """
    def __init__(self, layer, message, debug=False):
        self.layer = layer
        self.message = message
        self.debug = debug

    def __enter__(self):
        self.layer.startEditing()
        if self.debug:
            log_msg("BEGIN %s" % self.message)

    def __exit__(self, type, value, traceback):
        self.layer.commitChanges()
        self.layer.updateExtents()
        if self.debug:
            log_msg("END %s" % self.message)


class WaitCursorManager(object):
    """
    Wrapper to be used for a time-consuming block of code, that changes the
    mouse cursor and adds an info message to the messageBar
    """
    def __init__(self, msg=None, iface=None):
        self.msg = msg
        self.iface = iface
        self.has_message = msg and iface
        self.message = None

    def __enter__(self):
        if self.has_message:
            self.message = self.iface.messageBar().createMessage(
                tr('Info'), tr(self.msg))
            self.message = self.iface.messageBar().pushWidget(
                self.message, level=QgsMessageBar.INFO)
            QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)

    def __exit__(self, type, value, traceback):
        QApplication.restoreOverrideCursor()
        if self.has_message:
            self.iface.messageBar().popWidget(self.message)


class SvNetworkError(Exception):
    pass


class UserAbortedNotification(Exception):
    pass


class ReadMetadataError(Exception):
    """When a metadata xml is not correctly formatted can't be read"""
    suggestion = (
        'Check that the file is correct')


class IterableToFileAdapter(object):
    """ an adapter which makes the multipart-generator issued by poster
        accessible to requests. Based upon code from
        http://stackoverflow.com/a/13911048/1659732
        https://goo.gl/zgLx0T
    """
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = iterable.total

    def read(self, size=-1):
        return next(self.iterator, b'')

    def __len__(self):
        return self.length


def multipart_encode_for_requests(params, boundary=None, cb=None):
    """"helper function simulating the interface of posters
        multipart_encode()-function
        but wrapping its generator with the file-like adapter
    """
    data_generator, headers = multipart_encode(params, boundary, cb)
    return IterableToFileAdapter(data_generator), headers


def write_layer_suppl_info_to_qgs(layer_id, suppl_info):
    """
    Write into the QgsProject the given supplemental information, associating
    it with the given layer id.

    :param layer_id: id of the layer for which we want to update the
                     corresponding supplemental_information
    :param suppl_info: the supplemental information
    """
    # TODO: upgrade old project definitions
    # set the QgsProject's property
    QgsProject.instance().writeEntry(
        'irmt', layer_id,
        json.dumps(suppl_info,
                   sort_keys=False,
                   indent=2,
                   separators=(',', ': ')))

    # avoids not finding the layer_id in supplemental_info
    read_layer_suppl_info_from_qgs(layer_id, suppl_info)
    if DEBUG:
        prop_suppl_info, found = QgsProject.instance().readEntry('irmt',
                                                                 layer_id)
        assert found, 'After writeEntry, readEntry did not find the same item!'
        prop_suppl_info_obj = json.loads(prop_suppl_info)
        prop_suppl_info_str = pformat(prop_suppl_info_obj, indent=4)
        log_msg(("Project's property 'supplemental_information[%s]'"
                 " updated: \n%s") % (layer_id, prop_suppl_info_str))


def read_layer_suppl_info_from_qgs(layer_id, supplemental_information):
    """
    Read from the QgsProject the supplemental information associated to the
    given layer

    :param layer_id: the layer id for which we want to retrieve the
                     supplemental information
    :param supplemental_information: the supplemental information to be updated

    :returns: a tuple, with the returned supplemental information and a
              boolean indicating if such property is available
    """
    layer_suppl_info_str, _ = QgsProject.instance().readEntry(
        'irmt', layer_id, '{}')
    supplemental_information[layer_id] = json.loads(layer_suppl_info_str)

    if DEBUG:
        suppl_info_str = pformat(supplemental_information[layer_id], indent=4)
        log_msg(("self.supplemental_information[%s] synchronized"
                 " with project, as: \n%s") % (layer_id, suppl_info_str))


def insert_platform_layer_id(
        layer_url, active_layer_id, supplemental_information):
    """
    Insert the platform layer id into the supplemental information

    :param layer_url: url of the OpenQuake Platform layer
    :param active_layer_id: id of the QGIS layer that is currently selected
    :param supplemental_information: the supplemental information
    """
    platform_layer_id = layer_url.split('/')[-1]
    suppl_info = supplemental_information[active_layer_id]
    if 'platform_layer_id' not in suppl_info:
        suppl_info['platform_layer_id'] = platform_layer_id
    write_layer_suppl_info_to_qgs(active_layer_id, suppl_info)


def get_ui_class(ui_file):
    """Get UI Python class from .ui file.
       Can be filename.ui or subdirectory/filename.ui

    :param ui_file: The file of the ui in svir.ui
    :type ui_file: str
    """
    os.path.sep.join(ui_file.split('/'))
    ui_file_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            'ui',
            ui_file
        )
    )
    return uic.loadUiType(ui_file_path)[0]


def save_layer_setting(layer, setting, value):
    if layer is not None:
        QgsProject.instance().writeEntry(
            'irmt', '%s/%s' % (layer.id(), setting),
            json.dumps(value))


def get_layer_setting(layer, setting):
    if layer is not None:
        value_str, found = QgsProject.instance().readEntry(
            'irmt', '%s/%s' % (layer.id(), setting), '')
        if found and value_str:
            value = json.loads(value_str)
            return value
    return None


def save_layer_as_shapefile(orig_layer, dest_path, crs=None):
    if crs is None:
        crs = orig_layer.crs()
    old_lc_numeric = locale.getlocale(locale.LC_NUMERIC)
    locale.setlocale(locale.LC_NUMERIC, 'C')
    write_success = QgsVectorFileWriter.writeAsVectorFormat(
        orig_layer, dest_path, 'utf-8', crs, 'ESRI Shapefile')
    locale.setlocale(locale.LC_NUMERIC, old_lc_numeric)
    return write_success


def _check_type(
        variable, setting_name, expected_type, default_value, message_bar):
    # return the variable as it is or restore the default if corrupted
    if not isinstance(variable, expected_type):
        msg = ('The type of the stored setting "%s" was not valid,'
               ' so the default has been restored.' % setting_name)
        log_msg(msg, level='C', message_bar=message_bar)
        variable = default_value
    return variable


def get_style(layer, message_bar):
    color_from_rgba_default = QColor('#FFEBEB').rgba()
    color_to_rgba_default = QColor('red').rgba()
    style_mode_default = QgsGraduatedSymbolRendererV2.Quantile
    style_classes_default = 10
    force_restyling_default = True

    settings = QSettings()
    try:
        color_from_rgba = settings.value(
            'irmt/style_color_from', color_from_rgba_default, type=int)
    except TypeError:
        msg = ('The type of the stored setting "style_color_from" was not'
               ' valid, so the default has been restored.')
        log_msg(msg, level='C', message_bar=message_bar)
        color_from_rgba = color_from_rgba_default
    color_from = QColor().fromRgba(color_from_rgba)
    try:
        color_to_rgba = settings.value(
            'irmt/style_color_to', color_to_rgba_default, type=int)
    except TypeError:
        msg = ('The type of the stored setting "style_color_to" was not'
               ' valid, so the default has been restored.')
        log_msg(msg, level='C', message_bar=message_bar)
        color_to_rgba = color_to_rgba_default
    color_to = QColor().fromRgba(color_to_rgba)
    mode = settings.value(
        'irmt/style_mode', style_mode_default, type=int)
    classes = settings.value(
        'irmt/style_classes', style_classes_default, type=int)
    # look for the setting associated to the layer if available
    force_restyling = None
    if layer is not None:
        # NOTE: We can't use %s/%s instead of %s_%s, because / is a special
        #       character
        value, found = QgsProject.instance().readBoolEntry(
            'irmt', '%s_%s' % (layer.id(), 'force_restyling'))
        if found:
            force_restyling = value
    # otherwise look for the setting at project level
    if force_restyling is None:
        value, found = QgsProject.instance().readBoolEntry(
            'irmt', 'force_restyling')
        if found:
            force_restyling = value
    # if again the setting is not found, look for it at the general level
    if force_restyling is None:
        force_restyling = settings.value(
            'irmt/force_restyling', force_restyling_default, type=bool)
    return {
        'color_from': color_from,
        'color_to': color_to,
        'mode': mode,
        'classes': classes,
        'force_restyling': force_restyling
    }


def clear_widgets_from_layout(layout):
    """
    Recursively remove all widgets from the layout, except from nested
    layouts. If any of such widgets is a layout, then clear its widgets
    instead of deleting it.
    """
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        # check if the item is a sub-layout (nested inside the layout)
        sublayout = item.layout()
        if sublayout is not None:
            clear_widgets_from_layout(sublayout)
            continue
        # check if the item is a widget
        widget = item.widget()
        if widget is not None:
            # a widget is deleted when it does not have a parent
            widget.setParent(None)


def import_layer_from_csv(parent,
                          csv_path,
                          layer_name,
                          iface,
                          longitude_field='lon',
                          latitude_field='lat',
                          delimiter=',',
                          quote='"',
                          lines_to_skip_count=0,
                          wkt_field=None,
                          save_as_shp=False,
                          dest_shp=None,
                          zoom_to_layer=True):
    url = QUrl.fromLocalFile(csv_path)
    url.addQueryItem('type', 'csv')
    if wkt_field is not None:
        url.addQueryItem('wktField', wkt_field)
    else:
        url.addQueryItem('xField', longitude_field)
        url.addQueryItem('yField', latitude_field)
    url.addQueryItem('spatialIndex', 'no')
    url.addQueryItem('subsetIndex', 'no')
    url.addQueryItem('watchFile', 'no')
    url.addQueryItem('delimiter', delimiter)
    url.addQueryItem('quote', quote)
    url.addQueryItem('crs', 'epsg:4326')
    url.addQueryItem('skipLines', str(lines_to_skip_count))
    url.addQueryItem('trimFields', 'yes')
    layer_uri = str(url.toEncoded())
    layer = QgsVectorLayer(layer_uri, layer_name, "delimitedtext")
    if save_as_shp:
        dest_filename = dest_shp or QFileDialog.getSaveFileName(
            parent,
            'Save loss shapefile as...',
            os.path.expanduser("~"),
            'Shapefiles (*.shp)')
        if dest_filename:
            if dest_filename[-4:] != ".shp":
                dest_filename += ".shp"
        else:
            return
        result = save_layer_as_shapefile(layer, dest_filename)
        if result != QgsVectorFileWriter.NoError:
            raise RuntimeError('Could not save shapefile')
        layer = QgsVectorLayer(dest_filename, layer_name, 'ogr')
    if layer.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        iface.setActiveLayer(layer)
        if zoom_to_layer:
            iface.zoomToActiveLayer()

    else:
        msg = 'Unable to load layer'
        log_msg(msg, level='C', message_bar=iface.messageBar())
        return None
    return layer


def listdir_fullpath(path):
    return [os.path.join(path, filename) for filename in os.listdir(path)]


class InvalidHeaderError(Exception):
    pass


def get_params_from_comment_line(comment_line):
    """
    :param commented_line: a line starting with "# "
    :returns: an OrderedDict with parameter -> value

    >>> get_params_from_comment_line('# investigation_time=1000.0')
    OrderedDict([('investigation_time', '1000.0')])

    >>> get_params_from_comment_line("# p1=10, p2=20")
    OrderedDict([('p1', '10'), ('p2', '20')])

    >>> get_params_from_comment_line('h1, h2, h3')
    Traceback (most recent call last):
        ...
    InvalidHeaderError: Unable to extract parameters from line:
    h1, h2, h3
    because the line does not start with "# "

    >>> get_params_from_comment_line("# p1=10,p2=20")
    Traceback (most recent call last):
        ...
    InvalidHeaderError: Unable to extract parameters from line:
    # p1=10,p2=20
    """
    err_msg = 'Unable to extract parameters from line:\n%s' % comment_line
    if not comment_line.startswith('# '):
        raise InvalidHeaderError(
            err_msg + '\nbecause the line does not start with "# "')
    try:
        comment, rest = comment_line.split('# ', 1)
    except IndexError:
        raise InvalidHeaderError(err_msg)
    params_dict = collections.OrderedDict()
    param_defs = rest.split(', ')
    for param_def in param_defs:
        try:
            name, value = param_def.split('=')
        except ValueError:
            raise InvalidHeaderError(err_msg)
        else:
            params_dict[name] = value
    return params_dict
