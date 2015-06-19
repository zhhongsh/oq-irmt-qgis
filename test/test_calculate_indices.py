# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Svir
                                 A QGIS plugin
 OpenQuake Social Vulnerability and Integrated Risk
                              -------------------
        begin                : 2015-06-15
        copyright            : (C) 2015 by GEM Foundation
        email                : devops@openquake.org
 ***************************************************************************/

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
"""

import unittest
import os
from copy import deepcopy
from qgis.core import QgsVectorLayer
from calculate_utils import (calculate_node,
                             get_node_attr_id_and_name,
                             )
from process_layer import ProcessLayer
from utils import set_operator, get_node
from shared import OPERATORS_DICT


class CalculateCompositeVariableTestCase(unittest.TestCase):

    def setUp(self):

        self.project_definition = {
            "name": "IRI",
            "weight": 1.0,
            "level": "1.0",
            "operator": "Weighted sum",
            "type": "Integrated Risk Index",
            "children": [
                {"name": "RI",
                 "type": "Risk Index",
                 "children": [],
                 "weight": 0.5,
                 "level": "2.0"
                 },
                {"name": "SVI",
                 "type": "Social Vulnerability Index",
                 "children": [
                     {"name": "Education",
                      "weight": 0.5,
                      "level": "3.0",
                      "operator": "Weighted sum",
                      "type": "Social Vulnerability Theme",
                      "children": [
                          {"name": ("Female population without secondary"
                                    "education or higher"),
                           "isInverted": True,
                           "weight": 0.2,
                           "level": 4.0,
                           "field": "EDUEOCSAF",
                           "type": "Social Vulnerability Indicator",
                           "children": []
                           },
                          {"name": ("Male population without secondary"
                                    "education or higher"),
                           "isInverted": True,
                           "weight": 0.3,
                           "level": 4.0,
                           "field": "EDUEOCSAM",
                           "type": "Social Vulnerability Indicator",
                           "children": []
                           },
                          {"name": "Scientific and technical journal articles",
                           "weight": 0.5,
                           "level": 4.0,
                           "field": "EDUEOCSTJ",
                           "type": "Social Vulnerability Indicator",
                           "children": []
                           }
                      ]
                      },
                     {"name": "Environment",
                      "weight": 0.5,
                      "level": "3.0",
                      "operator": "Weighted sum",
                      "type": "Social Vulnerability Theme",
                      "children": [
                          {"name": "Droughts, floods, extreme temperatures",
                           "weight": 0.5,
                           "level": 4.1,
                           "field": "ENVDIPDFT",
                           "type": "Social Vulnerability Indicator",
                           "children": []
                           },
                          {"name": "Natural disasters  - Number of deaths",
                           "weight": 0.5,
                           "level": 4.1,
                           "field": "ENVDIPIND",
                           "type": "Social Vulnerability Indicator",
                           "children": []
                           }
                      ]
                      }
                 ],
                 "weight": 0.5,
                 "level": "2.0"
                 }
            ],
            "description": ""
        }

        # Load layer
        curr_dir_name = os.path.dirname(__file__)
        self.data_dir_name = os.path.join(curr_dir_name,
                                          'data/calculate_indices')
        layer_path = os.path.join(
            self.data_dir_name, 'socioeconomic_data.shp')
        orig_layer = QgsVectorLayer(layer_path, 'Zonal Layer', 'ogr')
        # Avoid modifying the original files
        self.layer = ProcessLayer(orig_layer).duplicate_in_memory()

    def test_simple_sum(self):
        proj_def = deepcopy(self.project_definition)
        operator = OPERATORS_DICT['SUM_S']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)

    def test_weighted_sum(self):
        proj_def = deepcopy(self.project_definition)
        operator = OPERATORS_DICT['SUM_W']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)

    def test_simple_multiplication(self):
        proj_def = deepcopy(self.project_definition)
        operator = OPERATORS_DICT['MUL_S']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)

    def test_weighted_multiplication(self):
        proj_def = deepcopy(self.project_definition)
        operator = OPERATORS_DICT['MUL_W']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)

    def test_average(self):
        proj_def = deepcopy(self.project_definition)
        operator = OPERATORS_DICT['AVG']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)

    def test_geometric_mean_positive_argument(self):
        proj_def = deepcopy(self.project_definition)
        operator = OPERATORS_DICT['GEOM_MEAN']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)

    def test_geometric_mean_negative_argument(self):
        proj_def = deepcopy(self.project_definition)
        # do not invert EDUEOCSAM ==> it should cause the geometric mean to
        # attempt calculating the root of a negative number, so we should have
        # the corresponding field discarded with 'Invalid value' reason
        assert proj_def['children'][1]['children'][0]['children'][1]['field'] \
            == 'EDUEOCSAM'
        #                   SVI            Education      EDUEOCSAM
        proj_def['children'][1]['children'][0]['children'][1]['isInverted'] \
            = False
        operator = OPERATORS_DICT['GEOM_MEAN']
        node_attr_id, node_attr_name, discarded_feats = \
            calculate(proj_def, operator, self.layer)


def calculate(proj_def, operator, layer):
    """
    Use the calculate_node function to compute the 'Education' node using the
    given project definition and operator.
    The layer is updated as a side effect.
    """
    # set all operators of proj_def to the one selected
    proj_def = set_operator(proj_def, operator)
    # we are testing the calculation for a single node
    education_node = get_node(proj_def, 'Education')
    node_attr_id, node_attr_name = get_node_attr_id_and_name(education_node,
                                                             layer)
    discarded_feats = set()
    discarded_feats = calculate_node(
        education_node, node_attr_name, node_attr_id,
        layer, discarded_feats)
    return node_attr_id, node_attr_name, discarded_feats
