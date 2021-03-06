# -*- coding: utf-8 -*-
# /***************************************************************************
# Irmt
#                                 A QGIS plugin
# OpenQuake Integrated Risk Modelling Toolkit
#                              -------------------
#        begin                : 2013-10-24
#        copyright            : (C) 2013-2019 by GEM Foundation
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

from qgis.core import (
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       )
from svir.processing_provider.transform_fields import TransformFieldsAlgorithm
from svir.calculations.transformation_algs import rank


class RankAlgorithm(TransformFieldsAlgorithm):

    INVERSE = 'INVERSE'
    VARIANT = 'VARIANT'

    def name(self):
        return 'rank'

    def displayName(self):
        return self.tr(
            "Data ranking of vector layer fields")

    def shortHelpString(self):
        return self.tr(
            "Data ranking is a simple standardization technique. It is not"
            " affected by outliers and it allows the performance of"
            " enumeration units to be benchmarked over time in terms of their"
            " relative positions (rankings).\n"
            "This algorithm ranks values of vector layer fields, dealing with"
            " ties using the chosen strategy (see"
            " <a href=\"https://en.wikipedia.org/wiki/Ranking#Strategies_for_assigning_rankings)\">Wikipedia</a>") # NOQA

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INVERSE,
                description=self.tr("Assign higher ranks to smaller values"),
                defaultValue=False,
            )
        )
        self.variants = (
            ('AVERAGE', self.tr('Average - Fractional (1 2.5 2.5 4)')),
            ('MIN', self.tr('Standard competition - Minimum (1224)')),
            ('MAX', self.tr('Modified competition - Maximum (1334)')),
            ('DENSE', self.tr('Dense (1223)')),
            ('ORDINAL', self.tr('Ordinal (1234)')))
        variant = QgsProcessingParameterEnum(
            self.VARIANT,
            self.tr('Tie strategy'),
            options=[p[1] for p in self.variants],
            allowMultiple=False, defaultValue=0, optional=False)
        self.addParameter(variant)

    def transform_values(self, original_values, parameters, context):
        inverse = self.parameterAsBool(parameters, self.INVERSE, context)
        variant = [self.variants[i][0]
                   for i in self.parameterAsEnums(
                       parameters, self.VARIANT, context)][0]
        original_non_missing = [value for value in original_values
                                if value is not None]
        transformed_non_missing, _ = rank(
            original_non_missing, inverse=inverse, variant_name=variant)
        transformed_values = [None] * len(original_values)
        j = 0
        for i in range(len(original_values)):
            if original_values[i] is None:
                continue
            transformed_values[i] = transformed_non_missing[j]
            j += 1
        return transformed_values
