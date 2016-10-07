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

import sys
import csv
import os
import time
import matplotlib.pyplot as plt
from collections import defaultdict

from PyQt4.QtCore import pyqtSlot, QSettings, QDir
from PyQt4.QtGui import (QDialog,
                         QFileDialog,
                         QDialogButtonBox)
from qgis.core import QgsMapLayer
from qgis.gui import QgsMessageBar
from svir.calculations.aggregate_loss_by_zone import add_zone_id_to_points

from svir.utilities.utils import (get_ui_class,
                                  read_config_file,
                                  reload_layers_in_cbx,
                                  reload_attrib_cbx,
                                  WaitCursorManager,
                                  tr,
                                  create_progress_message_bar,
                                  clear_progress_message_bar,
                                  )
from svir.recovery_modeling.building import Building

FORM_CLASS = get_ui_class('ui_recovery_modeling.ui')

DAYS_BEFORE_EVENT = 200
SVI_WEIGHT_COEFF = 1  # FIXME: Let the user set this parameter


class RecoveryModelingDialog(QDialog, FORM_CLASS):
    """
    Modal dialog giving to perform recovery modeling analysis.

    Object-oriented Programming(OOP) is used to model post-earthquake community
    recovery of residential community.

    PAOLO: FIXME In the last version, we only have a Building class
    In this Programming, four classes are
    adopted, namely Building Class, Ground Motion FIelds Class, Constructuon &
    Enigneering Service Class and Community Class.

    In each class, a set of data and functions work together to complete a task
    which we call attributes and functions.  Attribute is used to specify if
    and how object properties are accessed within the programming environment
    Function is used to create/altere to achieve task or functionality and
    return the attributes of an object

    Procedure of this OOP Programming:
    Step 1: Define attributes of objects in each class
    Step 2: Set up functions in each class
    Step 3: Incorporate Napa Data to community recovery model

    Methodology:
    Time-based method is utilized which characterize a probability density
    function of the time it takes to a higher or lower functioning state given
    a set of explanatory variables such as the extent of damage to the
    building.
    """
    def __init__(self, iface):
        QDialog.__init__(self)
        self.phlog=open(os.path.join(os.path.expanduser('~'),'irmt-ph-pt.log'),'w') 
        self.phlog.write('START sys.path=%s\n' % sys.path)
        self.iface = iface
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.ok_button = self.buttonBox.button(QDialogButtonBox.Ok)
        self.populate_approach_cbx()
        reload_layers_in_cbx(
            self.dmg_by_asset_layer_cbx, [QgsMapLayer.VectorLayer])
        reload_layers_in_cbx(self.svi_layer_cbx, [QgsMapLayer.VectorLayer])
        recovery_modeling_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'recovery_modeling')
        self.input_data_dir = os.path.join(recovery_modeling_dir, 'input_data')
        self.restoreState()
        self.set_ok_button()

    def restoreState(self):
        """
        Reinstate the options based on the user's stored session info.
        """
        mySettings = QSettings()
        output_data_dir = mySettings.value('irmt/recovery_output_data_dir', '')
        # hack for strange mac behaviour
        if not output_data_dir:
            output_data_dir = ''
        self.output_data_dir_le.setText(output_data_dir)

    def saveState(self):
        """
        Store the options into the user's stored session info.
        """
        mySettings = QSettings()
        mySettings.setValue('irmt/recovery_output_data_dir',
                            self.output_data_dir_le.text())

    def set_ok_button(self):
        self.ok_button.setEnabled(
            os.path.isdir(self.output_data_dir_le.text())
            and self.approach_cbx.currentIndex != -1)
        # and self.dmg_by_asset_layer_cbx.currentIndex != -1
        # and self.svi_layer_cbx.currentIndex != -1
        # and self.svi_field_name_cbx.currentIndex != -1
        # and self.zone_field_name_cbx.currentIndex != -1)

    def populate_approach_cbx(self):
        self.approach_cbx.addItems(['Aggregate', 'Disaggregate'])

    @pyqtSlot(str)
    def on_output_data_dir_le_textChanged(self, text):
        self.output_data_dir = self.output_data_dir_le.text()
        self.set_ok_button()

    @pyqtSlot(str)
    def on_approach_cbx_currentIndexChanged(self, selected_text):
        # TODO: we might need to ask the user to provide the necessary files
        self.set_ok_button()

    @pyqtSlot(int)
    def on_dmg_by_asset_layer_cbx_currentIndexChanged(self, selected_index):
        self.dmg_by_asset_layer = self.dmg_by_asset_layer_cbx.itemData(
            selected_index)

    @pyqtSlot(int)
    def on_svi_layer_cbx_currentIndexChanged(self, selected_index):
        self.svi_layer = self.svi_layer_cbx.itemData(selected_index)
        # FIXME self.svi_field_name is temporarily ignored
        # reload_attrib_cbx(self.svi_field_name_cbx, self.svi_layer)
        reload_attrib_cbx(self.zone_field_name_cbx, self.svi_layer)

    @pyqtSlot()
    def on_output_data_dir_btn_clicked(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr('Choose output directory'), QDir.homePath())
        if path:
            self.output_data_dir_le.setText(path)

    def read_all_configuration_files(self):
        self.phlog.write('read_all_configuration_files\n' % sys.path)
        self.phlog.flush()
        inspectionTimes = read_config_file('InspectionTimes.txt')
        assessmentTimes = read_config_file('AssessmentTimes.txt')
        mobilizationTimes = read_config_file('MobilizationTimes.txt')
        repairTimes = read_config_file('RepairTimes.txt')
        recoveryTimes = read_config_file('RecoveryTimes.txt')
        leadTimeDispersion = read_config_file(
            'LeadTimeDispersion.txt', float)
        repairTimeDispersion = read_config_file(
            'RepairTimeDispersion.txt', float)
        numberOfDamageSimulations = read_config_file(
            'NumberOfDamageSimulations.txt', int)[0]
        return (inspectionTimes, assessmentTimes, mobilizationTimes,
                repairTimes, recoveryTimes, leadTimeDispersion,
                repairTimeDispersion, numberOfDamageSimulations)

    def generate_community_level_recovery_curve(self, integrate_svi=True):
        # Developed By: Henry Burton
        # Edited by: Hua Kang
        # Reimplemented for this plugin by: Paolo Tormene and Marco Bernasocchi
        # Objective: GenerateCommunityLevelRecoveryCurve
        # Initial date: August 26, 2016

        self.phlog.write('generate_community_level_recovery_curve, integrate_svi=%s\n' % integrate_svi)

        if integrate_svi:
            self.svi_layer = self.svi_layer_cbx.itemData(
                    self.svi_layer_cbx.currentIndex())
            # FIXME self.svi_field_name is temporarily ignored
            # self.svi_field_name = self.svi_field_name_cbx.currentText()
            self.zone_field_name = self.zone_field_name_cbx.currentText()

        start = time.clock()  # FIXME
        # Step 1: Define attributes of objects in each class

        # Define Attributes of Constructuon & Engineering Service Class

        (inspectionTimes, assessmentTimes, mobilizationTimes, repairTimes,
         recoveryTimes, leadTimeDispersion, repairTimeDispersion,
         numberOfDamageSimulations) = self.read_all_configuration_files()

        # Step 3: Incorporate Napa Data to community recovery model

        # build dictionary zone_id -> dmg_by_asset
        zonal_dmg_by_asset = defaultdict(list)
        if integrate_svi:
            # FIXME self.svi_field_name is temporarily ignored
            # svi_by_zone = dict()
            for zone_feat in self.svi_layer.getFeatures():
                zone_id = str(zone_feat[self.zone_field_name])
                # FIXME self.svi_field_name is temporarily ignored
                # svi_value = zone_feat[self.svi_field_name]
                # svi_by_zone[zone_id] = svi_value
            msg = 'Reading damage state probabilities...'
            msg_bar_item, progress = create_progress_message_bar(
                self.iface.messageBar(), msg)
            tot_features = self.dmg_by_asset_layer.featureCount()
            self.phlog.write('generate_community_level_recovery_curve, tot_features=%s\n' % tot_features)
            for feat_idx, dmg_by_asset_feat in enumerate(
                    self.dmg_by_asset_layer.getFeatures()):
                progress_perc = feat_idx / float(tot_features) * 100
                self.phlog.write('generate_community_level_recovery_curve, progress=%s\n' % progress_perc)
                self.phlog.flush()
                progress.setValue(progress_perc)
                zone_id = dmg_by_asset_feat[self.zone_field_name]
                # FIXME: hack to handle case in which the zone id is an integer
                # but it is stored as Real
                try:
                    zone_id = str(int(zone_id))
                except:
                    zone_id = str(zone_id)
                self.phlog.write('generate_community_level_recovery_curve, zone_id=%s\n' % zone_id)
                self.phlog.flush()
                # select fields that contain probabilities
                # i.e., ignore asset id and taxonomy (first 2 items)
                # and get only columns containing means, discarding
                # those containing stddevs, therefore getting one item
                # out of two for the remaining columns
                # Also discard the last field, containing zone ids
                dmg_by_asset_probs = dmg_by_asset_feat.attributes()[
                    2:-1:2]
                self.phlog.write('generate_community_level_recovery_curve, len(dmg_by_asset_probs)=%s \n' % len(dmg_by_asset_probs))
                self.phlog.flush()
                zonal_dmg_by_asset[zone_id].append(dmg_by_asset_probs)
                self.phlog.write('generate_community_level_recovery_curve, appended probs to zonal_dmg_by_asset\n')
                self.phlog.flush()
            self.phlog.write('generate_community_level_recovery_curve 526\n')
            self.phlog.flush()
            clear_progress_message_bar(self.iface.messageBar(), msg_bar_item)
        else:  # ignore svi
            msg = 'Reading damage state probabilities...'
            msg_bar_item, progress = create_progress_message_bar(
                self.iface.messageBar(), msg)
            tot_features = self.dmg_by_asset_layer.featureCount()
            for idx, dmg_by_asset_feat in enumerate(
                    self.dmg_by_asset_layer.getFeatures()):
                progress_perc = idx / float(tot_features) * 100
                progress.setValue(progress_perc)
                # we don't have any field containing zone ids, to be discarded
                dmg_by_asset_probs = dmg_by_asset_feat.attributes()[2::2]
                zonal_dmg_by_asset['ALL'].append(dmg_by_asset_probs)
            clear_progress_message_bar(self.iface.messageBar(), msg_bar_item)

        tot_zones = len(zonal_dmg_by_asset)
        self.phlog.write('generate_community_level_recovery_curve, tot_zones=%s\n' % tot_zones)
        self.phlog.flush()
        msg = 'Calculating zone-level recovery curves...'
        msg_bar_item, progress = create_progress_message_bar(
            self.iface.messageBar(), msg)
        # for each zone, calculate a zone-level recovery function
        for idx, zone_id in enumerate(zonal_dmg_by_asset.keys()):
            progress_perc = idx / float(tot_zones) * 100
            progress.setValue(progress_perc)

            # TODO: use svi_by_zone[zone_id] to adjust recovery times (how?)

            self.phlog.write('generate_community_level_recovery_curve, 514 zone_id=%s idx=%s\n' % (zone_id,idx))
            self.phlog.flush()
            dmg_by_asset = zonal_dmg_by_asset[zone_id]

            (LossBasedDamageStateProbabilities,
             RecoveryBasedDamageStateProbabilities,
             fractionCollapsedAndIrreparableBuildings) = \
                self.loss_based_to_recovery_based_probs(dmg_by_asset)

            self.phlog.write('generate_community_level_recovery_curve, 516 zone_id=%s, fractionCollapsedAndIrreparableBuildings=%s\n' % (zone_id,fractionCollapsedAndIrreparableBuildings))
            self.phlog.flush()
            # FIXME self.svi_field_name is temporarily ignored
            # svi_value = svi_by_zone[zone_id] if integrate_svi else None

            # FIXME PH this brutal hack is here to fix problem with 
            # times increasing accross zones, there must be a better solution
            self.phlog.write('generate_community_level_recovery_curve, 556 zone_id=%s, re-reading config files\n' % zone_id)
            self.phlog.flush()
            (inspectionTimes, assessmentTimes, mobilizationTimes, repairTimes,
             recoveryTimes, leadTimeDispersion, repairTimeDispersion,
             numberOfDamageSimulations) = self.read_all_configuration_files()

            # FIXME - when aggregating by zone we are constantly increasing 
            # the times with this approach
            (timeList, inspectionTimes,
             assessmentTimes, mobilizationTimes) = self.calculate_times(
                fractionCollapsedAndIrreparableBuildings, inspectionTimes,
                assessmentTimes, mobilizationTimes, repairTimes)
            # assessmentTimes, mobilizationTimes, repairTimes, svi_value)

            # Initialize community recovery function
            communityRecoveryFunction = [0 for x in range(len(timeList))]
            New_communityRecoveryFunction = [
                0 for x in range(len(timeList)+DAYS_BEFORE_EVENT)]

            # self.generate_building_level_recovery_curve()  # FIXME
            # Looping over all damage simulations
            for sim in range(numberOfDamageSimulations):
                buildingLevelRecoveryFunction = \
                    self.generate_building_level_recovery_curve(
                        timeList, LossBasedDamageStateProbabilities,
                        RecoveryBasedDamageStateProbabilities, inspectionTimes,
                        recoveryTimes, repairTimes, leadTimeDispersion,
                        repairTimeDispersion, assessmentTimes,
                        mobilizationTimes)
                # Sum up all building level recovery function
                # TODO: use enumerate instead
                for timePoint in range(len(timeList)):
                    communityRecoveryFunction[timePoint] \
                        += buildingLevelRecoveryFunction[timePoint]

            # PAOLO: instead of calculating the community level recovery
            # function on all points, we should aggregate points by the same
            # zones defined for the socioeconomic dataset, and then we should
            # produce a community recovery function for each zone.
            # This has to be done on the damage by asset layer
            # (For the aggregation we can use SAGA:
            #  "Add Polygon Attributes to Points", i.e.
            #  processing.runalg('saga:addpolygonattributestopoints', input,
            #                    polygons, field, output))

            # Calculate community level recovery function
            # TODO: use enumerate instead
            for timePoint in range(len(timeList)):
                communityRecoveryFunction[timePoint] /= \
                    numberOfDamageSimulations

            # PAOLO: should we plot this?
            # Plot community level recovery curve
            # plt.plot(timeList, communityRecoveryFunction)
            # plt.show()

            # Plot community level recovery curve which can presents the number
            # of occupants before earthquake
            New_timeList = [x for x in range(len(timeList)+DAYS_BEFORE_EVENT)]
            # TODO: use enumerate instead
            for i in range(len(timeList)+DAYS_BEFORE_EVENT):
                if i < DAYS_BEFORE_EVENT:
                    New_communityRecoveryFunction[i] = 1
                else:
                    # FIXME - PH ugly check for 0 length: zones with < 2 assets
                    if len(LossBasedDamageStateProbabilities) < 1:
                        New_communityRecoveryFunction[i] = \
                            communityRecoveryFunction[i - DAYS_BEFORE_EVENT]
                    else:
                        New_communityRecoveryFunction[i] = (
                            communityRecoveryFunction[i - DAYS_BEFORE_EVENT]
                            / len(LossBasedDamageStateProbabilities))

            fig = plt.figure()
            plt.plot(New_timeList, New_communityRecoveryFunction)
            plt.xlabel('Time (days)')
            plt.ylabel('Normalized recovery level')
            plt.title('Community level recovery curve for zone %s' % zone_id)
            plt.ylim((0.0, 1.2))
            # plt.show()
            filestem = os.path.join(
                self.output_data_dir, "recovery_function_zone_%s" % zone_id)
            fig.savefig(filestem + '.png')

            # Save community recovery function
            f3 = open(filestem + '.txt', "w")
            f3.write(str(communityRecoveryFunction))
            f3.close()

            end = time.clock()
            print (end - start)
        clear_progress_message_bar(self.iface.messageBar(), msg_bar_item)

    def generate_building_level_recovery_curve(
            self, timeList, LossBasedDamageStateProbabilities,
            RecoveryBasedDamageStateProbabilities, inspectionTimes,
            recoveryTimes, repairTimes, leadTimeDispersion,
            repairTimeDispersion, assessmentTimes, mobilizationTimes):
        # Looping over all buildings in community
        # Initialize building level recovery function
        buildingLevelRecoveryFunction = [
            0 for x in range(len(timeList))]
        # TODO: use enumerate instead
        for bldg in range(len(LossBasedDamageStateProbabilities)):
            # Generate recovery function for current
            # building/simulation using the given damage state
            # probability distribution
            currentSimulationBuildingLevelDamageStateProbabilities = \
                RecoveryBasedDamageStateProbabilities[bldg]
            # call building class within Napa Data
            # PAOLO: building number is not used. Instead, we need to
            # make available to the building all the imported data
            napa_bldg = Building(
                inspectionTimes, recoveryTimes, repairTimes,
                leadTimeDispersion, repairTimeDispersion,
                currentSimulationBuildingLevelDamageStateProbabilities,
                timeList, assessmentTimes, mobilizationTimes)
            approach = self.approach_cbx.currentText()
            # approach can be aggregate or disaggregate
            z = napa_bldg.generateBldgLevelRecoveryFunction(approach)
            # The following lines plot building level curves
            # fig = plt.figure()
            # plt.plot(timeList, z)
            # plt.xlabel('Time (days)')
            # plt.ylabel('Normalized recovery level')
            # plt.title('Building level recovery curve')
            # plt.ylim((0.0, 1.2))
            # plt.show()
            # Assign buidling level recovery function
            # TODO: use enumerate instead
            for timePoint in range(len(timeList)):
                buildingLevelRecoveryFunction[timePoint] += z[
                    timePoint]
        return buildingLevelRecoveryFunction

    def loss_based_to_recovery_based_probs(self, dmg_by_asset):
        self.phlog.write('loss_based_to_recovery_based_probs, len dmg_by_asset=%s\n' % len(dmg_by_asset))
        self.phlog.flush()

        LossBasedDamageStateProbabilities = [
            [0 for x in range(5)] for y in range(len(dmg_by_asset)-1)]

        for i in range(len(dmg_by_asset)-1):
            for j in range(5):
                LossBasedDamageStateProbabilities[i][j] = \
                    dmg_by_asset[i+1][j]  # was dmg_by_asset[i+1][j+4]

        # Load Transfer Probability Note: There is a 5*6 matrix where rows
        # describe loss-based damage states (No
        # damage/Slight/Moderate/Extensive/Complete) and columns present
        # recovery-based damage states(No damage/Trigger inspection/Loss
        # Function /Not Occupiable/Irreparable/Collapse). The element(i,j)
        # in the matrix is the probability of recovery-based damage state j
        # occurs given loss-based damage state i

        transferProbabilitiesData = os.path.join(
            self.input_data_dir, 'transferProbabilities.csv')

        with open(transferProbabilitiesData, 'r') as f:
            reader = csv.reader(f)
            transferProbabilities = list(reader)

        # Mapping from Loss-based to recovery-based building damage states
        RecoveryBasedDamageStateProbabilities = [
            [0 for x in range(6)] for y in range(len(dmg_by_asset)-1)]

        fractionCollapsedAndIrreparableBuildings = 0
        # TODO: use enumerate instead
        for i in range(len(LossBasedDamageStateProbabilities)):
            for j in range(len(transferProbabilities[0])):
                for s in range(len(transferProbabilities)):
                    RecoveryBasedDamageStateProbabilities[i][j] += (
                        float(LossBasedDamageStateProbabilities[i][s])
                        * float(transferProbabilities[s][j]))
                    if j == 4 or j == 5:
                        fractionCollapsedAndIrreparableBuildings += \
                            RecoveryBasedDamageStateProbabilities[i][j]

        if len(dmg_by_asset) < 2:
            self.phlog.write('loss_based_to_recovery_based_probs, dmg_by_asset len <2 fractionCollapsedAndIrreparableBuildings=%s \n' % fractionCollapsedAndIrreparableBuildings)
            self.phlog.flush()
	else:
            fractionCollapsedAndIrreparableBuildings = \
                fractionCollapsedAndIrreparableBuildings / (
                    len(dmg_by_asset)-1)
        return (LossBasedDamageStateProbabilities,
                RecoveryBasedDamageStateProbabilities,
                fractionCollapsedAndIrreparableBuildings)

    def calculate_times(
            self, fractionCollapsedAndIrreparableBuildings,
            inspectionTimes, assessmentTimes, mobilizationTimes,
            repairTimes):  # FIXME self.svi_field_name is temporarily ignored
            # repairTimes, svi_value):
        # PAOLO and VENETIA: the paper refers to a metodology by Comerio
        # (2006): "a performance index can be developed to relate the
        # fraction of collapsed buildings within a particular region, and
        # used to account for delays caused by regional socioeconomic
        # effects" Since we will multiply results by a social vulnerability
        # index, we are wondering if this correction is still needed.
        # Otherwise, we can keep this, and add a further correction when we
        # take into account the socioeconomic index.

        # Compute lead time adjustment factor
        # FIXME: HB said that 0.5, 2.31 and 0.22 are parameters based on an
        # empirical equation. We could simplify the formula, if those
        # parameters don't have any clear meaning as they are
        leadTimeFactor = 0.5 * (
            2.31 + 0.22 * fractionCollapsedAndIrreparableBuildings
            * 100) / 2.31

        self.phlog.write('calculate_times: leadTimeFactor=%s\n' % leadTimeFactor)
        self.phlog.flush()
        # Generate Time Vector Used for Recovery Function
        # Maximum time in days

        maxTime = (int(max(inspectionTimes))
                   + int(max(assessmentTimes))
                   + int(max(mobilizationTimes))
                   + int(max(repairTimes)) + DAYS_BEFORE_EVENT * 2)

        self.phlog.write('calculate_times: maxTime=%s\n' % maxTime)
	self.phlog.write(' max(inspectionTimes)=%s\n ' % int(max(inspectionTimes)) )
	self.phlog.write(' max(assessmentTimes)=%s\n ' % int(max(assessmentTimes)) )
	self.phlog.write(' max(mobilizationTimes)=%s\n ' % int(max(mobilizationTimes)) )
	self.phlog.write(' max(repairTimes)=%s\n ' % int(max(repairTimes)) )
        self.phlog.flush()
        self.phlog.write('calculate_times: len(inspectionTimes)=%s\n' % len(inspectionTimes))
        self.phlog.flush()
        # PAOLO: TODO We have to find a proper way to use the SVI to adjust the
        # recovery times. For now we are not using it, but we are aggregating
        # assets by the same zones for which the SVI is defined
        # if svi_value:
        #     maxTime = int(round(maxTime * SVI_WEIGHT_COEFF * svi_value))

        # Time List
        timeList = range(maxTime)

        # Calculate lead time by mutiply lead time factor
        # TODO: use enumerate instead4
        # FIXME: PH is it really correct to modify inspectionTimes et al here?  
        # The effect is to constantly increase the times in the lists
        # (see also below)
        for i in range(len(inspectionTimes)):
            inspectionTimes[i] = leadTimeFactor * float(inspectionTimes[i])
            assessmentTimes[i] = leadTimeFactor * float(assessmentTimes[i])
            mobilizationTimes[i] = (
                leadTimeFactor * float(mobilizationTimes[i]))
        return (timeList, inspectionTimes, assessmentTimes, mobilizationTimes)

    def accept(self):
        if self.integrate_svi_check.isChecked():
            self.zone_field_name = self.zone_field_name_cbx.currentText()
            (_, self.dmg_by_asset_layer, self.svi_layer,
             self.zone_field_name) = add_zone_id_to_points(
                self.iface, None, self.dmg_by_asset_layer,
                self.svi_layer, None, self.zone_field_name)
        with WaitCursorManager('Generating recovery curves...', self.iface):
            self.generate_community_level_recovery_curve(
                self.integrate_svi_check.isChecked())
        self.phlog.flush()
        self.iface.messageBar().pushMessage(
            tr("Info"),
            'Recovery curves have been saved to [%s]' % self.output_data_dir,
            level=QgsMessageBar.INFO, duration=0)
        self.saveState()
        super(RecoveryModelingDialog, self).accept()
