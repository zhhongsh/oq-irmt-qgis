# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 2013-10-24
#        copyright            : (C) 2014 by GEM Foundation
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
from qgis.core import QgsFeature, QgsGeometry, QgsPoint
from svir.dialogs.load_output_as_layer_dialog import LoadOutputAsLayerDialog
from svir.calculations.calculate_utils import add_numeric_attribute
from svir.utilities.utils import (WaitCursorManager,
                                  LayerEditingManager,
                                  log_msg,
                                  groupby,
                                  )
from svir.utilities.shared import DEBUG


class LoadLossesByAssetAsLayerDialog(LoadOutputAsLayerDialog):
    """
    Modal dialog to load losses by asset from an oq-engine output, as layer
    """

    def __init__(
            self, iface, output_type='losses_by_asset', path=None, mode=None):
        assert output_type == 'losses_by_asset'
        LoadOutputAsLayerDialog.__init__(self, iface, output_type, path, mode)
        self.setWindowTitle(
            'Load losses by asset from NPZ, aggregated by location, as layer')
        self.create_load_selected_only_ckb()
        self.create_rlz_selector()
        self.create_taxonomy_selector()
        self.create_loss_type_selector()
        if self.path:
            self.npz_file = numpy.load(self.path, 'r')
            self.populate_out_dep_widgets()
        self.adjustSize()
        self.set_ok_button()

    def set_ok_button(self):
        self.ok_button.setEnabled(bool(self.path))

    def on_rlz_changed(self):
        self.dataset = self.npz_file[self.rlz_cbx.currentText()]
        self.taxonomies = numpy.unique(self.dataset['taxonomy']).tolist()
        self.populate_taxonomy_cbx(self.taxonomies)
        # discarding 'asset_ref', 'taxonomy', 'lon', 'lat'
        self.loss_types = self.dataset.dtype.names[4:]
        self.populate_loss_type_cbx(self.loss_types)
        self.set_ok_button()

    def populate_rlz_cbx(self):
        self.rlzs = [key for key in self.npz_file.keys()
                     if key.startswith('rlz')]
        self.rlz_cbx.clear()
        self.rlz_cbx.setEnabled(True)
        self.rlz_cbx.addItems(self.rlzs)

    def populate_taxonomy_cbx(self, taxonomies):
        taxonomies.insert(0, 'All')
        self.taxonomy_cbx.clear()
        self.taxonomy_cbx.addItems(taxonomies)
        self.taxonomy_cbx.setEnabled(True)

    def build_layer_name(self, rlz, **kwargs):
        taxonomy = kwargs['taxonomy']
        loss_type = kwargs['loss_type']
        layer_name = "losses_by_asset_%s_%s_%s" % (
            rlz, taxonomy, loss_type)
        return layer_name

    def get_field_names(self, **kwargs):
        # field_names = list(self.dataset.dtype.names)
        loss_type = kwargs['loss_type']
        field_names = ['lon', 'lat', loss_type]
        self.default_field_name = loss_type
        return field_names

    def add_field_to_layer(self, field_name):
        # NOTE: add_numeric_attribute uses LayerEditingManager
        added_field_name = add_numeric_attribute(
            field_name, self.layer)
        return added_field_name

    def read_npz_into_layer(self, field_names, **kwargs):
        rlz = kwargs['rlz']
        loss_type = kwargs['loss_type']
        taxonomy = kwargs['taxonomy']
        with LayerEditingManager(self.layer, 'Reading npz', DEBUG):
            feats = []
            grouped_by_site = groupby(
                self.npz_file, rlz, loss_type, taxonomy)
            for row in grouped_by_site:
                # add a feature
                feat = QgsFeature(self.layer.pendingFields())
                for field_name_idx, field_name in enumerate(field_names):
                    if field_name in ['lon', 'lat']:
                        continue
                    value = float(row[field_name_idx])
                    feat.setAttribute(field_names[field_name_idx], value)
                feat.setGeometry(QgsGeometry.fromPoint(
                    QgsPoint(row['lon'], row['lat'])))
                feats.append(feat)
            added_ok = self.layer.addFeatures(feats, makeSelected=False)
            if not added_ok:
                msg = 'There was a problem adding features to the layer.'
                log_msg(msg, level='C', message_bar=self.iface.messageBar())

    def load_from_npz(self):
        for rlz in self.rlzs:
            if (self.load_selected_only_ckb.isChecked()
                    and rlz != self.rlz_cbx.currentText()):
                continue
            for taxonomy in self.taxonomies:
                if (self.load_selected_only_ckb.isChecked()
                        and taxonomy != self.taxonomy_cbx.currentText()):
                    continue
                for loss_type in self.loss_types:
                    if (self.load_selected_only_ckb.isChecked()
                            and loss_type != self.loss_type_cbx.currentText()):
                        continue
                    with WaitCursorManager(
                            'Creating layer for realization "%s", '
                            ' taxonomy "%s" and loss type "%s"...' % (
                            rlz, taxonomy, loss_type), self.iface):
                        self.build_layer(
                            rlz, taxonomy=taxonomy, loss_type=loss_type)
                        self.style_maps()
                        # if self.output_type == 'loss_curves':
                        #     self.style_curves()
                        # elif self.output_type == 'loss_maps':
                        #     self.style_maps()
        if self.npz_file is not None:
            self.npz_file.close()