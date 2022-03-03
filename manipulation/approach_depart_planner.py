import os
import math
import copy
import pickle
import numpy as np
import basis.data_adapter as da
import modeling.collision_model as cm
import motion.optimization_based.incremental_nik as inik
import motion.probabilistic.rrt_connect as rrtc


class ADPlanner(object):  # AD = Approach_Depart

    def __init__(self, robot_s):
        """
        :param robot_s:

        """
        self.robot_s = robot_s
        self.inik_slvr = inik.IncrementalNIK(self.robot_s)
        self.rrtc_planner = rrtc.RRTConnect(self.robot_s)

    def gen_jawwidth_motion(self, conf_list, jawwidth):
        jawwidth_list = []
        for _ in conf_list:
            jawwidth_list.append(jawwidth)
        return jawwidth_list

    def gen_approach_linear(self,
                            component_name,
                            goal_tcp_pos,
                            goal_tcp_rotmat,
                            approach_direction=None,  # np.array([0, 0, -1])
                            approach_distance=.1,
                            approach_jawwidth=.05,
                            granularity=0.03,
                            obstacle_list=[],
                            seed_jnt_values=None,
                            toggle_end_grasp=False,
                            end_jawwidth=.0):
        """

        :param component_name:
        :param goal_tcp_pos:
        :param goal_tcp_rotmat:
        :param approach_direction:
        :param approach_distance:
        :param approach_jawwidth:
        :param granularity:
        :param toggle_end_grasp:
        :param end_jawwidth: only used when toggle_end_grasp is True
        :return:

        """
        if approach_direction is None:
            approach_direction = goal_tcp_rotmat[:, 2]
        conf_list = self.inik_slvr.gen_rel_linear_motion(component_name,
                                                         goal_tcp_pos,
                                                         goal_tcp_rotmat,
                                                         approach_direction,
                                                         approach_distance,
                                                         obstacle_list=obstacle_list,
                                                         granularity=granularity,
                                                         type='sink',
                                                         seed_jnt_values=seed_jnt_values)
        if conf_list is None:
            print('Cannot perform approach linear!')
            return None, None
        else:
            if toggle_end_grasp:
                jawwidth_list = self.gen_jawwidth_motion(conf_list, approach_jawwidth)
                conf_list += [conf_list[-1]]
                jawwidth_list += [end_jawwidth]
                return conf_list, jawwidth_list
            else:
                return conf_list, self.gen_jawwidth_motion(conf_list, approach_jawwidth)

    def gen_depart_linear(self,
                          component_name,
                          start_tcp_pos,
                          start_tcp_rotmat,
                          depart_direction=None,  # np.array([0, 0, 1])
                          depart_distance=.1,
                          depart_jawwidth=.05,
                          granularity=0.03,
                          obstacle_list=[],
                          seed_jnt_values=None,
                          toggle_begin_grasp=False,
                          begin_jawwidth=.0):
        """

        :param component_name:
        :param goal_tcp_pos:
        :param goal_tcp_rotmat:
        :param depart_direction:
        :param depart_distance:
        :param depart_jawwidth:
        :param granularity:
        :param seed_jnt_values:
        :param toggle_begin_grasp:
        :param begin_jawwidth: only used when toggle_end_grasp is True
        :return: conf_list, jawwidth_list, objhomomat_list_list

        """
        if depart_direction is None:
            depart_direction = -start_tcp_rotmat[:, 2]
        conf_list = self.inik_slvr.gen_rel_linear_motion(component_name,
                                                         start_tcp_pos,
                                                         start_tcp_rotmat,
                                                         depart_direction,
                                                         depart_distance,
                                                         obstacle_list=obstacle_list,
                                                         granularity=granularity,
                                                         type='source',
                                                         seed_jnt_values=seed_jnt_values)
        if conf_list is None:
            print('Cannot perform depart action!')
            return None, None
        else:
            if toggle_begin_grasp:
                jawwidth_list = self.gen_jawwidth_motion(conf_list, depart_jawwidth)
                conf_list = [conf_list[0]] + conf_list
                jawwidth_list = [begin_jawwidth] + jawwidth_list
                return conf_list, jawwidth_list
            else:
                return conf_list, self.gen_jawwidth_motion(conf_list, depart_jawwidth)

    def gen_approach_and_depart_linear(self,
                                       component_name,
                                       goal_tcp_pos,
                                       goal_tcp_rotmat,
                                       approach_direction=None,  # np.array([0, 0, -1])
                                       approach_distance=.1,
                                       approach_jawwidth=.05,
                                       depart_direction=None,  # np.array([0, 0, 1])
                                       depart_distance=.1,
                                       depart_jawwidth=0,
                                       granularity=.03,
                                       obstacle_list=[],
                                       seed_jnt_values=None):
        """
        :param component_name:
        :param goal_tcp_pos:
        :param goal_tcp_rotmat:
        :param hnd_name:
        :param approach_direction:
        :param approach_distance:
        :param approach_jawwidth:
        :param depart_direction:
        :param depart_distance:
        :param depart_jawwidth:
        :param granularity:
        :return: approach_conf_list, depart_jawwidth_list

        """
        if approach_direction is None:
            approach_direction = goal_tcp_rotmat[:, 2]
        approach_conf_list = self.inik_slvr.gen_rel_linear_motion(component_name,
                                                                  goal_tcp_pos,
                                                                  goal_tcp_rotmat,
                                                                  approach_direction,
                                                                  approach_distance,
                                                                  obstacle_list=obstacle_list,
                                                                  granularity=granularity,
                                                                  type='sink',
                                                                  seed_jnt_values=seed_jnt_values)
        if approach_distance != 0 and len(approach_conf_list) == 0:
            print('Cannot perform approach action!')
        else:
            if depart_direction is None:
                depart_direction = goal_tcp_rotmat[:, 2]
            depart_conf_list = self.inik_slvr.gen_rel_linear_motion(component_name,
                                                                    goal_tcp_pos,
                                                                    goal_tcp_rotmat,
                                                                    depart_direction,
                                                                    depart_distance,
                                                                    obstacle_list=obstacle_list,
                                                                    granularity=granularity,
                                                                    type='source',
                                                                    seed_jnt_values=approach_conf_list[-1])
            if depart_distance != 0 and len(depart_conf_list) == 0:
                print('Cannot perform depart action!')
            else:
                approach_jawwidth_list = self.gen_jawwidth_motion(approach_conf_list, approach_jawwidth)
                depart_jawwidth_list = self.gen_jawwidth_motion(depart_conf_list, depart_jawwidth)
                return approach_conf_list + depart_conf_list, approach_jawwidth_list + depart_jawwidth_list
        return [], []

    def gen_approach_motion(self,
                            component_name,
                            goal_tcp_pos,
                            goal_tcp_rotmat,
                            start_conf=None,
                            approach_direction=None,  # np.array([0, 0, -1])
                            approach_distance=.1,
                            approach_jawwidth=.05,
                            granularity=.03,
                            obstacle_list=[], # obstacles, will be checked by both rrt and linear
                            object_list=[], # target objects, will be checked by rrt, but not by linear
                            seed_jnt_values=None,
                            toggle_end_grasp=False,
                            end_jawwidth=.0):
        if seed_jnt_values is None:
            seed_jnt_values = start_conf
        if approach_direction is None:
            approach_direction = goal_tcp_rotmat[:, 2]
        conf_list, jawwidth_list = self.gen_approach_linear(component_name,
                                                            goal_tcp_pos,
                                                            goal_tcp_rotmat,
                                                            approach_direction,
                                                            approach_distance,
                                                            approach_jawwidth,
                                                            granularity,
                                                            obstacle_list,
                                                            seed_jnt_values,
                                                            toggle_end_grasp,
                                                            end_jawwidth)
        if conf_list is None:
            print("ADPlanner: Cannot gen approach linear!")
            return None, None
        if start_conf is not None:
            start2approach_conf_list = self.rrtc_planner.plan(component_name=component_name,
                                                              start_conf=start_conf,
                                                              goal_conf=conf_list[0],
                                                              obstacle_list=obstacle_list+object_list,
                                                              ext_dist=.05,
                                                              max_time=300)
            if start2approach_conf_list is None:
                print("ADPlanner: Cannot plan approach motion!")
                return None, None
            start2approach_jawwidth_list = self.gen_jawwidth_motion(start2approach_conf_list, approach_jawwidth)
        return start2approach_conf_list + conf_list, start2approach_jawwidth_list + jawwidth_list

    def gen_depart_motion(self,
                          component_name,
                          start_tcp_pos,
                          start_tcp_rotmat,
                          end_conf=None,
                          depart_direction=None,  # np.array([0, 0, 1])
                          depart_distance=.1,
                          depart_jawwidth=.05,
                          granularity=.03,
                          obstacle_list=[],  # obstacles, will be checked by both rrt and linear
                          object_list=[],  # target objects, will be checked by rrt, but not by linear
                          seed_jnt_values=None,
                          toggle_begin_grasp=False,
                          begin_jawwidth=.0):
        if seed_jnt_values is None:
            seed_jnt_values = end_conf
        if depart_direction is None:
            depart_direction = start_tcp_rotmat[:, 2]
        conf_list, jawwidth_list = self.gen_depart_linear(component_name,
                                                          start_tcp_pos,
                                                          start_tcp_rotmat,
                                                          depart_direction,
                                                          depart_distance,
                                                          depart_jawwidth,
                                                          granularity,
                                                          obstacle_list,
                                                          seed_jnt_values,
                                                          toggle_begin_grasp,
                                                          begin_jawwidth)
        if conf_list is None:
            print("ADPlanner: Cannot gen depart linear!")
            return None, None
        if end_conf is not None:
            depart2goal_conf_list = self.rrtc_planner.plan(component_name=component_name,
                                                           start_conf=conf_list[-1],
                                                           goal_conf=end_conf,
                                                           obstacle_list=obstacle_list+object_list,
                                                           ext_dist=.05,
                                                           max_time=300)
            if depart2goal_conf_list is None:
                print("ADPlanner: Cannot plan depart motion!")
                return None, None
            depart2goal_jawwidth_list = self.gen_jawwidth_motion(depart2goal_conf_list, depart_jawwidth)
        else:
            depart2goal_conf_list = []
            depart2goal_jawwidth_list = []
        return conf_list + depart2goal_conf_list, jawwidth_list + depart2goal_jawwidth_list

    def gen_approach_and_depart_motion(self,
                                       component_name,
                                       goal_tcp_pos,
                                       goal_tcp_rotmat,
                                       start_conf=None,
                                       goal_conf=None,
                                       approach_direction=None,  # np.array([0, 0, -1])
                                       approach_distance=.1,
                                       approach_jawwidth=.05,
                                       depart_direction=None,  # np.array([0, 0, 1])
                                       depart_distance=.1,
                                       depart_jawwidth=0,
                                       granularity=.03,
                                       obstacle_list=[],  # obstacles, will be checked by both rrt and linear
                                       object_list=[],  # target objects, will be checked by rrt, but not by linear
                                       seed_jnt_values=None):
        """
        degenerate into gen_ad_primitive if both seed_jnt_values and end_conf are None
        :param component_name:
        :param goal_tcp_pos:
        :param goal_tcp_rotmat:
        :param start_conf:
        :param goal_conf:
        :param approach_direction:
        :param approach_distance:
        :param approach_jawwidth:
        :param depart_direction:
        :param depart_distance:
        :param depart_jawwidth:
        :param granularity:
        :param seed_jnt_values:
        :param obstacle_list:
        :return:

        """
        if seed_jnt_values is None:
            seed_jnt_values = start_conf
        if approach_direction is None:
            approach_direction = goal_tcp_rotmat[:, 2]
        if depart_direction is None:
            approach_direction = -goal_tcp_rotmat[:, 2]
        ad_conf_list, ad_jawwidth_list = self.gen_approach_and_depart_linear(component_name,
                                                                             goal_tcp_pos,
                                                                             goal_tcp_rotmat,
                                                                             approach_direction,
                                                                             approach_distance,
                                                                             approach_jawwidth,
                                                                             depart_direction,
                                                                             depart_distance,
                                                                             depart_jawwidth,
                                                                             granularity,
                                                                             obstacle_list,
                                                                             seed_jnt_values)
        if ad_conf_list is None:
            print("ADPlanner: Cannot gen ad linear!")
            return None, None
        if start_conf is not None:
            start2approach_conf_list = self.rrtc_planner.plan(component_name=component_name,
                                                              start_conf=start_conf,
                                                              goal_conf=ad_conf_list[0],
                                                              obstacle_list=obstacle_list,
                                                              # object_list=object_list,
                                                              ext_dist=.05,
                                                              max_time=300)
            if start2approach_conf_list is None:
                print("ADPlanner: Cannot plan approach motion!")
                return None, None
            start2approach_jawwidth_list = self.gen_jawwidth_motion(start2approach_conf_list, approach_jawwidth)
        if goal_conf is not None:
            depart2goal_conf_list = self.rrtc_planner.plan(component_name=component_name,
                                                           start_conf=ad_conf_list[-1],
                                                           goal_conf=goal_conf,
                                                           obstacle_list=obstacle_list,
                                                           # object_list=object_list,
                                                           ext_dist=.05,
                                                           max_time=300)
            if depart2goal_conf_list is None:
                print("ADPlanner: Cannot plan depart motion!")
                return None, None
            depart2goal_jawwidth_list = self.gen_jawwidth_motion(depart2goal_conf_list, depart_jawwidth)
        return start2approach_conf_list + ad_conf_list + depart2goal_conf_list, \
               start2approach_jawwidth_list + ad_jawwidth_list + depart2goal_jawwidth_list

    def gen_depart_and_approach_linear(self):
        pass

    def gen_depart_and_approach_motion(self):
        pass

