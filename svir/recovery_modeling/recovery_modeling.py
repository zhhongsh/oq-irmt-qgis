
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

import os
import csv
import bisect
import matplotlib.pyplot as plt
from collections import defaultdict
from svir.recovery_modeling.building import Building
from svir.utilities.utils import (
                                  create_progress_message_bar,
                                  read_config_file,
                                  clear_progress_message_bar,
                                  )

DAYS_BEFORE_EVENT = 200
SVI_WEIGHT_COEFF = 1  # FIXME: Let the user set this parameter


class RecoveryModeling(object):
    """
    Object-oriented Programming(OOP) is used to model post-earthquake community
    recovery of residential community.

    Methodology:
    Time-based method is utilized which characterize a probability density
    function of the time it takes to a higher or lower functioning state given
    a set of explanatory variables such as the extent of damage to the
    building.
    """

    def __init__(self, dmg_by_asset_layer, svi_layer, approach,
                 output_data_dir, iface):
        self.iface = iface
        self.svi_layer = svi_layer
        self.dmg_by_asset_layer = dmg_by_asset_layer
        self.approach = approach
        self.output_data_dir = output_data_dir
        recovery_modeling_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'recovery_modeling')
        self.input_data_dir = os.path.join(recovery_modeling_dir, 'input_data')

    def collect_zonal_data(self, integrate_svi=False, zone_field_name=None):

        # build dictionary zone_id -> dmg_by_asset_probs
        zonal_dmg_by_asset_probs = defaultdict(list)
        zonal_asset_refs = defaultdict(list)
        if integrate_svi:
            # FIXME self.svi_field_name is temporarily ignored
            # svi_by_zone = dict()
            for zone_feat in self.svi_layer.getFeatures():
                zone_id = str(zone_feat[zone_field_name])
                # FIXME self.svi_field_name is temporarily ignored
                # svi_value = zone_feat[self.svi_field_name]
                # svi_by_zone[zone_id] = svi_value
            msg = 'Reading damage state probabilities...'
            msg_bar_item, progress = create_progress_message_bar(
                self.iface.messageBar(), msg)
            tot_features = self.dmg_by_asset_layer.featureCount()
            for feat_idx, dmg_by_asset_feat in enumerate(
                    self.dmg_by_asset_layer.getFeatures(), start=1):
                zone_id = dmg_by_asset_feat[zone_field_name]
                # FIXME: hack to handle case in which the zone id is an integer
                # but it is stored as Real
                try:
                    zone_id = str(int(zone_id))
                except:
                    zone_id = str(zone_id)
                # FIXME: same hack as above
                asset_ref = dmg_by_asset_feat['asset_ref']
                try:
                    asset_ref = str(int(asset_ref))
                except:
                    asset_ref = str(asset_ref)
                # select fields that contain probabilities
                # i.e., ignore asset id and taxonomy (first 2 items)
                # and get only columns containing means, discarding
                # those containing stddevs, therefore getting one item
                # out of two for the remaining columns
                # Also discard the last field, containing zone ids
                dmg_by_asset_probs = dmg_by_asset_feat.attributes()[
                    2:-1:2]
                zonal_dmg_by_asset_probs[zone_id].append(dmg_by_asset_probs)
                zonal_asset_refs[zone_id].append(asset_ref)
                progress_perc = feat_idx / float(tot_features) * 100
                progress.setValue(progress_perc)
            clear_progress_message_bar(self.iface.messageBar(), msg_bar_item)
        else:  # ignore svi
            msg = 'Reading damage state probabilities...'
            msg_bar_item, progress = create_progress_message_bar(
                self.iface.messageBar(), msg)
            tot_features = self.dmg_by_asset_layer.featureCount()
            for idx, dmg_by_asset_feat in enumerate(
                    self.dmg_by_asset_layer.getFeatures(), start=1):
                # we don't have any field containing zone ids, to be discarded
                dmg_by_asset_probs = dmg_by_asset_feat.attributes()[2::2]
                asset_ref = dmg_by_asset_feat['asset_ref']
                zonal_dmg_by_asset_probs['ALL'].append(dmg_by_asset_probs)
                zonal_asset_refs['ALL'].append(asset_ref)
                progress_perc = idx / float(tot_features) * 100
                progress.setValue(progress_perc)
            clear_progress_message_bar(self.iface.messageBar(), msg_bar_item)
        return zonal_dmg_by_asset_probs, zonal_asset_refs

    def read_all_configuration_files(self):
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

    def generate_community_level_recovery_curve(
            self, zone_id, zonal_dmg_by_asset_probs,
            zonal_asset_refs, writer, integrate_svi=True):

        # TODO: use svi_by_zone[zone_id] to adjust recovery times (how?)

        dmg_by_asset_probs = zonal_dmg_by_asset_probs[zone_id]
        asset_refs = zonal_asset_refs[zone_id]

        (LossBasedDamageStateProbabilities,
            RecoveryBasedDamageStateProbabilities,
            fractionCollapsedAndIrreparableBuildings) = \
            self.loss_based_to_recovery_based_probs(dmg_by_asset_probs)

        # FIXME self.svi_field_name is temporarily ignored
        # svi_value = svi_by_zone[zone_id] if integrate_svi else None

        # FIXME If we don't read files again for each zone, time increases
        # across zones. This is not optimal, but configuration files are
        # very small, so reading them is almost instantaneous.
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

        # Looping over all damage simulations
        for sim in range(numberOfDamageSimulations):
            simulationRecoveryFunction = \
                self.generate_simulation_recovery_curve(
                    timeList, LossBasedDamageStateProbabilities,
                    RecoveryBasedDamageStateProbabilities, inspectionTimes,
                    recoveryTimes, repairTimes, leadTimeDispersion,
                    repairTimeDispersion, assessmentTimes,
                    mobilizationTimes, zone_id, asset_refs)
            # Sum up all building level recovery function
            # TODO: use enumerate instead
            for timePoint in range(len(timeList)):
                communityRecoveryFunction[timePoint] \
                    += simulationRecoveryFunction[timePoint]

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
                New_communityRecoveryFunction[i] = (
                    communityRecoveryFunction[i - DAYS_BEFORE_EVENT]
                    / len(LossBasedDamageStateProbabilities))

        fig = plt.figure()
        # highlight values at observation days (after 6, 12 and 18 months)
        obs_days = [DAYS_BEFORE_EVENT + day for day in (0, 180, 360, 540)]
        xlabels = ['event', '6 months', '12 months', '18 months']
        plt.plot(New_timeList, New_communityRecoveryFunction)
        row = [zone_id]
        for obs_day in obs_days:
            value_at_obs_day = New_communityRecoveryFunction[obs_day]
            row.append(value_at_obs_day)
            if obs_day != DAYS_BEFORE_EVENT:  # no vertical line at event time
                plt.axvline(x=obs_day, linestyle='dotted')
            i = obs_day
            j = value_at_obs_day
            plt.annotate(
                '%.3f' % j,
                xy=(i, j),
                xytext=(-35, 5),
                textcoords='offset points')
        # TODO: add x value and vertical line when y is 95% recovery
        for day in [DAYS_BEFORE_EVENT + day for day in timeList]:
            value = New_communityRecoveryFunction[day]
            if value > 0.95:
                plt.axvline(x=day, linestyle='dashed')
                # insert day in obs_days at the right ordered index
                position = bisect.bisect(obs_days, day)
                bisect.insort(obs_days, day)
                xlabels.insert(position, "%s days" % (day - DAYS_BEFORE_EVENT))
                break
        writer.writerow(row)
        plt.xticks(obs_days, xlabels, rotation='vertical')
        plt.xlabel('Time (days)')
        # plt.set_xticklabels(labels)
        plt.ylabel('Normalized recovery level')
        plt.title('Community level recovery curve for zone %s' % zone_id)
        plt.ylim((0.0, 1.2))
        plt.tight_layout()
        # plot_margin = 1.25
        # x0, x1, y0, y1 = plt.axis()
        # plt.axis((x0 - plot_margin,
        #           x1 + plot_margin,
        #           y0 - plot_margin,
        #           y1 + plot_margin))
        # plt.show()
        filestem = os.path.join(
            self.output_data_dir, "recovery_function_zone_%s" % zone_id)
        fig.savefig(filestem + '.png')

        # Save community recovery function
        f3 = open(filestem + '.txt', "w")
        f3.write(str(New_communityRecoveryFunction))
        f3.close()

    def generate_simulation_recovery_curve(
            self, timeList, LossBasedDamageStateProbabilities,
            RecoveryBasedDamageStateProbabilities, inspectionTimes,
            recoveryTimes, repairTimes, leadTimeDispersion,
            repairTimeDispersion, assessmentTimes, mobilizationTimes,
            zone_id, asset_refs):
        # Looping over all buildings in community
        # Initialize building level recovery function
        simulationRecoveryFunction = [
            0 for x in range(len(timeList))]
        # TODO: use enumerate instead
        # TODO: perhaps iterate enumerating by asset_ref
        for bldg_idx in range(len(LossBasedDamageStateProbabilities)):
            # Generate recovery function for current
            # building/simulation using the given damage state
            # probability distribution
            currentSimulationBuildingLevelDamageStateProbabilities = \
                RecoveryBasedDamageStateProbabilities[bldg_idx]
            # call building class within Napa Data
            # PAOLO: building number is not used. Instead, we need to
            # make available to the building all the imported data
            napa_bldg = Building(
                inspectionTimes, recoveryTimes, repairTimes,
                leadTimeDispersion, repairTimeDispersion,
                currentSimulationBuildingLevelDamageStateProbabilities,
                timeList, assessmentTimes, mobilizationTimes)
            approach = self.approach
            # approach can be aggregate or disaggregate
            building_level_recovery_function = \
                napa_bldg.generateBldgLevelRecoveryFunction(approach)
            output_by_building_dir = os.path.join(
                self.output_data_dir, 'by_building')
            if not os.path.exists(output_by_building_dir):
                os.makedirs(output_by_building_dir)
            asset_ref = asset_refs[bldg_idx]
            output_filename = os.path.join(
                output_by_building_dir,
                "zone_%s_bldg_%s.txt" % (zone_id, asset_ref))
            with open(output_filename, 'w') as f:
                f.write(str(building_level_recovery_function))
            # The following lines plot building level curves
            # fig = plt.figure()
            # plt.plot(timeList, building_level_recovery_function)
            # plt.xlabel('Time (days)')
            # plt.ylabel('Normalized recovery level')
            # plt.title('Building level recovery curve')
            # plt.ylim((0.0, 1.2))
            # plt.show()
            # Assign buidling level recovery function
            # TODO: use enumerate instead
            for timePoint in range(len(timeList)):
                simulationRecoveryFunction[timePoint] += \
                    building_level_recovery_function[timePoint]
        return simulationRecoveryFunction

    def loss_based_to_recovery_based_probs(self, dmg_by_asset_probs):
        LossBasedDamageStateProbabilities = [
            [0 for x in range(5)] for y in range(len(dmg_by_asset_probs))]

        for i in range(len(dmg_by_asset_probs)):
            for j in range(5):
                LossBasedDamageStateProbabilities[i][j] = \
                    dmg_by_asset_probs[i][j]  # ex dmg_by_asset_probs[i+1][j+4]

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
            [0 for x in range(6)] for y in range(len(dmg_by_asset_probs))]

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

        fractionCollapsedAndIrreparableBuildings = \
            fractionCollapsedAndIrreparableBuildings / len(dmg_by_asset_probs)
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

        # Generate Time Vector Used for Recovery Function
        # Maximum time in days

        maxTime = (int(max(inspectionTimes))
                   + int(max(assessmentTimes))
                   + int(max(mobilizationTimes))
                   + int(max(repairTimes)) + DAYS_BEFORE_EVENT * 2)

        # PAOLO: TODO We have to find a proper way to use the SVI to adjust the
        # recovery times. For now we are not using it, but we are aggregating
        # assets by the same zones for which the SVI is defined
        # if svi_value:
        #     maxTime = int(round(maxTime * SVI_WEIGHT_COEFF * svi_value))

        # Time List
        timeList = range(maxTime)

        # Calculate lead time by mutiply lead time factor
        # TODO: use enumerate instead
        for i in range(len(inspectionTimes)):
            inspectionTimes[i] = leadTimeFactor * float(inspectionTimes[i])
            assessmentTimes[i] = leadTimeFactor * float(assessmentTimes[i])
            mobilizationTimes[i] = (
                leadTimeFactor * float(mobilizationTimes[i]))
        return (timeList, inspectionTimes, assessmentTimes, mobilizationTimes)