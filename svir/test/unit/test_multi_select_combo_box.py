# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 2013-10-24
#        copyright            : (C) 2019 by GEM Foundation
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

import unittest
from qgis.PyQt.QtWidgets import QWidget
from svir.ui.multi_select_combo_box import MultiSelectComboBox


class MultiSelectComboBoxMultiTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.wdg = QWidget()
        cls.mscb = MultiSelectComboBox(cls.wdg)

    def setUp(self):
        self.mscb.clear()

    def test_addItem(self):
        self.mscb.addItem('first name', selected=True)
        self.mscb.addItem('second name', selected=False)
        self.assertEqual(self.mscb.get_selected_items(), ['first name'])
        self.assertEqual(self.mscb.get_unselected_items(), ['second name'])

    def test_addItems(self):
        self.mscb.addItems(['first name', 'second name'], selected=True)
        self.assertEqual(
            self.mscb.get_selected_items(), ['first name', 'second name'])
        self.assertEqual(self.mscb.count(), 2)
        self.mscb.addItems(['third name', 'fourth name'], selected=False)
        self.assertEqual(
            self.mscb.get_selected_items(), ['first name', 'second name'])
        self.assertEqual(
            self.mscb.get_unselected_items(), ['third name', 'fourth name'])
        self.assertEqual(self.mscb.count(), 4)

    def test_add_selected_items(self):
        self.mscb.add_selected_items(['first name', 'second name'])
        self.assertEqual(
            self.mscb.get_selected_items(), ['first name', 'second name'])
        self.assertEqual(self.mscb.count(), 2)

    def test_add_unselected_items(self):
        self.mscb.add_unselected_items(['third name', 'fourth name'])
        self.assertEqual(
            self.mscb.get_unselected_items(), ['third name', 'fourth name'])
        self.assertEqual(self.mscb.count(), 2)

    def test_clear(self):
        self.mscb.add_selected_items(['first name', 'second name'])
        self.mscb.add_unselected_items(['third name', 'fourth name'])
        self.assertEqual(self.mscb.count(), 4)
        self.mscb.clear()
        self.assertEqual(self.mscb.count(), 0)

    def test_count(self):
        self.assertEqual(self.mscb.count(), 0)
        self.mscb.add_selected_items(['first name', 'second name'])
        self.mscb.add_unselected_items(['third name', 'fourth name'])
        self.assertEqual(self.mscb.count(), 4)

    def test_currentText(self):
        pass

    def test_get_selected_items(self):
        pass

    def test_get_unselected_items(self):
        pass

    def test_resetSelection(self):
        pass

    def test_selected_count(self):
        pass

    def test_setCurrentText(self):
        pass

    def test_set_idxs_selection(self):
        pass

    def test_set_items_selection(self):
        pass

    def test_set_selected_items(self):
        pass

    def test_set_unselected_items(self):
        pass


class MultiSelectComboBoxMonoTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.wdg = QWidget()
        cls.mscb = MultiSelectComboBox(cls.wdg, mono=True)

    def test_fixme(self):
        pass


if __name__ == '__main__':
    unittest.main()
