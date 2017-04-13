# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 201-10-24
#        copyright            : (C) 2014-2017 by GEM Foundation
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

# import qgis libs so that we set the correct sip api version
import os
import unittest
import tempfile
import filecmp

from PyQt4.QtGui import QAction
from qgis.core import QgsMapLayerRegistry, QgsVectorLayer
from svir.dialogs.load_dmg_by_asset_as_layer_dialog import (
    LoadDmgByAssetAsLayerDialog)
from svir.dialogs.load_ruptures_as_layer_dialog import (
    LoadRupturesAsLayerDialog)
from svir.dialogs.load_hmaps_as_layer_dialog import (
    LoadHazardMapsAsLayerDialog)
from svir.dialogs.load_hcurves_as_layer_dialog import (
    LoadHazardCurvesAsLayerDialog)
from svir.dialogs.load_gmf_data_as_layer_dialog import (
    LoadGmfDataAsLayerDialog)
from svir.dialogs.load_uhs_as_layer_dialog import (
    LoadUhsAsLayerDialog)
from svir.dialogs.viewer_dock import ViewerDock
from svir.calculations.process_layer import ProcessLayer
from utilities import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class LoadOQEngineOutputAsLayerTestCase(unittest.TestCase):
    def setUp(self):
        IFACE.newProject()
        curr_dir_name = os.path.dirname(__file__)
        self.data_dir_name = os.path.join(
            curr_dir_name, 'data')
        mock_action = QAction(IFACE.mainWindow())
        self.viewer_dock = ViewerDock(IFACE, mock_action)

    def tearDown(self):
        # the following line removes all the existing map layers
        IFACE.newProject()

    def test_load_hazard_map(self):
        filepath = os.path.join(
            self.data_dir_name, 'hazard', 'output-182-hmaps_67.npz')
        dlg = LoadHazardMapsAsLayerDialog(IFACE, 'hmaps', filepath)
        dlg.accept()
        # hazard maps have nothing to do with the Data Viewer

    def test_load_gmf(self):
        filepath = os.path.join(self.data_dir_name, 'hazard',
                                'output-195-gmf_data_70.npz')
        dlg = LoadGmfDataAsLayerDialog(IFACE, 'gmf_data', filepath)
        dlg.accept()
        # ground motion fields have nothing to do with the Data Viewer

    def test_load_hazard_curves(self):
        filepath = os.path.join(self.data_dir_name, 'hazard',
                                'output-181-hcurves_67.npz')
        dlg = LoadHazardCurvesAsLayerDialog(IFACE, 'hcurves', filepath)
        dlg.accept()
        self._set_output_type('Hazard Curves')
        self._change_selection()
        # test changing intensity measure type
        layers = CANVAS.layers()
        layer = layers[-1]
        # select the first 2 features (the same used to produce the reference
        # csv)
        layer.select([1, 2])
        imt = 'SA(0.2)'
        idx = self.viewer_dock.imt_cbx.findText(imt)
        self.assertNotEqual(idx, -1, 'IMT %s not found' % imt)
        self.viewer_dock.imt_cbx.setCurrentIndex(idx)
        # test exporting the current selection to csv
        _, exported_file_path = tempfile.mkstemp(suffix=".csv")
        self._test_export('hazard_curves_SA(0.2).csv')

    def test_load_uhs_only_selected_poe(self):
        filepath = os.path.join(self.data_dir_name, 'hazard',
                                'output-184-uhs_67.npz')
        dlg = LoadUhsAsLayerDialog(IFACE, 'uhs', filepath)
        dlg.load_selected_only_ckb.setChecked(True)
        idx = dlg.poe_cbx.findText('0.02')
        self.assertEqual(idx, 1, 'POE 0.02 was not found')
        dlg.poe_cbx.setCurrentIndex(idx)
        dlg.accept()
        self._set_output_type('Uniform Hazard Spectra')
        self._change_selection()
        # test exporting the current selection to csv
        self._test_export('uniform_hazard_spectra.csv')

    def test_load_uhs_all(self):
        filepath = os.path.join(self.data_dir_name, 'hazard',
                                'output-184-uhs_67.npz')
        dlg = LoadUhsAsLayerDialog(IFACE, 'uhs', filepath)
        dlg.load_selected_only_ckb.setChecked(False)
        dlg.accept()
        # FIXME: setActiveLayer is not working. As a workaround, I am deleting
        # all layers except the one I am testing.
        for layer in CANVAS.layers():
            if layer.name() != u'uhs_rlz-000_poe-0.02':
                QgsMapLayerRegistry.instance().removeMapLayer(layer)
        CANVAS.refresh()
        self._set_output_type('Uniform Hazard Spectra')
        self._change_selection()
        # test exporting the current selection to csv
        self._test_export('uniform_hazard_spectra.csv')

    def test_dmg_by_asset(self):
        filepath = os.path.join(
            self.data_dir_name, 'risk',
            'output-308-dmg_by_asset-ChiouYoungs2008()_103.csv')
        dlg = LoadDmgByAssetAsLayerDialog(
            IFACE, 'dmg_by_asset', filepath, mode='testing')
        dlg.save_as_shp_ckb.setChecked(True)
        idx = dlg.dmg_state_cbx.findText('complete')
        self.assertEqual(idx, 2, '"complete" damage state was not found')
        dlg.dmg_state_cbx.setCurrentIndex(idx)
        idx = dlg.loss_type_cbx.findText('structural')
        self.assertEqual(idx, 0, '"structural" loss_type was not found')
        dlg.loss_type_cbx.setCurrentIndex(idx)
        dlg.accept()
        current_layer = CANVAS.layers()[0]
        reference_path = os.path.join(
            self.data_dir_name, 'dmg_by_asset_complete_structural.shp')
        reference_layer = QgsVectorLayer(
            reference_path, 'dmg_by_asset_complete_structural', 'ogr')
        ProcessLayer(current_layer).has_same_content_as(reference_layer)

    def test_load_ruptures(self):
        filepath = os.path.join(
            self.data_dir_name, 'hazard', 'output-316-ruptures_104.csv')
        dlg = LoadRupturesAsLayerDialog(
            IFACE, 'ruptures', filepath, mode='testing')
        dlg.save_as_shp_ckb.setChecked(True)
        dlg.accept()
        current_layer = CANVAS.layers()[0]
        reference_path = os.path.join(
            self.data_dir_name, 'hazard', 'ruptures.shp')
        reference_layer = QgsVectorLayer(
            reference_path, 'reference_ruptures', 'ogr')
        ProcessLayer(current_layer).has_same_content_as(reference_layer)

    def _test_export(self, expected_file_name):
        _, exported_file_path = tempfile.mkstemp(suffix=".csv")
        layers = CANVAS.layers()
        layer = layers[-1]
        # select the first 2 features (the same used to produce the reference
        # csv)
        layer.select([1, 2])
        # probably we have the wrong layer selected (uhs produce many layers)
        self.viewer_dock.write_export_file(exported_file_path)
        expected_file_path = os.path.join(
            self.data_dir_name, 'hazard', expected_file_name)
        self.assertTrue(
            filecmp.cmp(exported_file_path, expected_file_path),
            'The exported file (%s) is different with respect to the'
            ' reference one (%s)' % (exported_file_path, expected_file_path))

    def _set_output_type(self, output_type):
        idx = self.viewer_dock.output_type_cbx.findText(output_type)
        self.assertNotEqual(idx, -1, 'Output type %s not found' % output_type)
        self.viewer_dock.output_type_cbx.setCurrentIndex(idx)

    def _change_selection(self):
        layers = CANVAS.layers()
        layer = layers[-1]
        # the behavior should be slightly different (pluralizing labels, etc)
        # depending on the amount of features selected
        layer.select(1)
        layer.select(2)
        layer.selectAll()
        layer.removeSelection()