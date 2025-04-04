# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
import math
import mathutils
from mathutils import *
from .QMeshOperators import *
from ..utils import pqutil

class QSnap:
    instance = None
    ref = 0

    @classmethod
    def add_ref(cls, context):
        if cls.ref == 0:
            cls.instance = cls(context)
            cls.update(context)
        cls.ref = cls.ref + 1

    @classmethod
    def remove_ref(cls):
        cls.ref = cls.ref - 1
        if cls.ref == 0 :
            if cls.instance :
                del cls.instance
                cls.instance = None

    @classmethod
    def is_active(cls) :
        return cls.instance != None

    @classmethod
    def update(cls,context) :
        if cls.instance :
            cls.instance.__update(context)

    def __init__(self, context, snap_objects = 'Visible'):
        self.objects_array = None
        self.bvh_list = None

    def __update(self, context) :
        if not self.isEnableSnap(context):
            self.remove_tree()
            return

        if self.bvh_list != None:
            if set(self.bvh_list.keys()) == set(self.snap_objects(context)):
                return

        self.remove_tree()
        self.create_tree(context)

    def isEnableSnap(self, context):
        ts = context.scene.tool_settings
        if not ts.use_snap:
            return False
        #if not 'FACE' in ts.snap_elements:
        #    return False
        return True

    @staticmethod
    def snap_objects(context):
        active = context.active_object
        a = []
        for obj in context.visible_objects:
            if obj != active and obj.type == 'MESH':
                a.append(obj)
        return a

    def create_tree(self, context):
        if self.bvh_list != None:
            return
        self.bvh_list = {}
        for obj in self.snap_objects(context):
            bvh = mathutils.bvhtree.BVHTree.FromObject(obj, context.evaluated_depsgraph_get(), epsilon = 0.0)
            self.bvh_list[obj] = bvh

    def remove_tree(self) :
        if self.bvh_list == None:
            return
        for bvh in self.bvh_list.values():
            del bvh
        self.bvh_list = None


    @classmethod
    def view_adjust( cls , world_pos : mathutils.Vector ) -> mathutils.Vector :
        if cls.instance != None :
            ray = pqutil.Ray.from_world_to_screen( bpy.context , world_pos )
            if ray == None :
                return world_pos
            location , norm , obj = cls.instance.__raycast(ray, None)
            if location != None :
                return location
        return world_pos

    @classmethod
    def adjust_point(cls, world_pos : mathutils.Vector, is_fix_to_x_zero = False):
        if cls.instance == None:
            return world_pos
        location , norm , index = cls.instance.__find_nearest( world_pos )
        if is_fix_to_x_zero and QMeshOperators.is_x_zero_pos(location) :
            location.x = 0
        return location

    @classmethod
    def adjust_local(cls, matrix_world : mathutils.Matrix, local_pos : mathutils.Vector, is_fix_to_x_zero):
        if cls.instance == None:
            return local_pos
        location, norm, index = cls.instance.__find_nearest(matrix_world @ local_pos)
        lp = matrix_world.inverted() @ location
        if is_fix_to_x_zero and QMeshOperators.is_x_zero_pos(local_pos):
            lp.x = 0
        return lp

    @classmethod
    def adjust_local_to_world(cls, matrix_world : mathutils.Matrix, local_pos : mathutils.Vector, is_fix_to_x_zero):
        if cls.instance == None:
            return local_pos
        location , norm , index = cls.instance.__find_nearest( matrix_world @ local_pos )
        lp = location
        if is_fix_to_x_zero and QMeshOperators.is_x_zero_pos(local_pos) :
            lp.x = 0
        return lp

    @classmethod
    def adjust_verts(cls, obj, verts, is_fix_to_x_zero):
        if cls.instance == None:
            return
        if not cls.instance.bvh_list:
            return

        dist = bpy.context.scene.tool_settings.double_threshold                        
        find_nearest =  cls.instance.__find_nearest
        matrix = obj.matrix_world
        for vert in verts :
            location , norm , index = find_nearest( matrix @ vert.co )
            if location != None :
                lp = obj.matrix_world.inverted() @ location
                if is_fix_to_x_zero and QMeshOperators.is_x_zero_pos(vert.co) :
                    lp.x = 0
                vert.co = lp

    @classmethod
    def is_target(cls, world_pos : mathutils.Vector, pickTarget) -> bool:
        dist = bpy.context.scene.tool_settings.double_threshold
        if cls.instance == None:
            return True

        ray = pqutil.Ray.from_world_to_screen(bpy.context, world_pos)
        if ray == None:
            return False

        hit, normal, face = cls.instance.__raycast(ray, pickTarget)
        if hit == None:
            return True

        v2h = (ray.origin - hit).length
        v2w = (ray.origin - world_pos).length
        if abs(v2h - v2w) <= dist:
            return True

        ray2 = pqutil.Ray(hit + ray.vector * dist, ray.vector)
        hit2, normal2, face2 = cls.instance.__raycast(ray2, pickTarget)
        if not hit2:
            return False
        h2h = (ray2.origin - hit2).length
        w2h0 = (ray2.origin - world_pos).length
        w2h1 = (world_pos - hit2).length
        if w2h0 >= h2h:
            return False
        if w2h0 >= w2h1:
            return False
        return True

    def __raycast(self, ray : pqutil.Ray, pickTarget):
        if not self.bvh_list:
            return None, None, None

        min_dist = math.inf
        location = None
        normal = None
        index = None
        for obj, bvh in self.bvh_list.items():
            if pickTarget:
                if not obj is pickTarget:
                    continue
            local_ray = ray.world_to_object(obj)
            hit = bvh.ray_cast(local_ray.origin, local_ray.vector)
            if None in hit:
                continue
            if hit[3] < min_dist:
                matrix = obj.matrix_world
                location = pqutil.transform_position( hit[0] , matrix )
                normal = pqutil.transform_normal( hit[1] , matrix )
                index =  hit[2] + obj.pass_index * 10000000
                min_dist = hit[3]

        return location, normal, index

    def __smart_find( self , ray : pqutil.Ray ) :
        location_i , normal_i , obj_i = self.__raycast_double( ray )
        if location_i == None :
            a,b,c = self.__find_nearest( ray.origin )
            return a,b,c
        location_r , normal_r , obj_r = self.__find_nearest( ray.origin )
        if location_r == None :
            return location_i , normal_i , obj_i
        if (location_r - ray.origin).length <= (location_i - ray.origin).length :
            return location_r , normal_r , obj_r
        else :
            return location_i , normal_i , obj_i        

    def __raycast_double( self , ray : pqutil.Ray ) :
        # ターゲットからビュー方向にレイを飛ばす
        location_r , normal_r , face_r = self.__raycast( ray )
        location_i , normal_i , face_i = self.__raycast( ray.invert )

        if None in [face_i,face_r] :
            if face_i != None :
                return location_i , normal_i , face_i
            elif face_r != None :
                return location_r , normal_r , face_r
        else :
            if (location_r - ray.origin).length <= (location_i - ray.origin).length :
                return location_r , normal_r , face_r
            else :
                return location_i , normal_i , face_i
        return None , None , None

    def __find_nearest(self, pos : mathutils.Vector):
        if not self.bvh_list:
            return pos, None, None

        min_dist = math.inf
        location = pos
        normal = None
        index = None
        for obj, bvh in self.bvh_list.items():
            lp = obj.matrix_world.inverted() @ pos
            hit = bvh.find_nearest(lp)
            if None not in hit:
                wp = pqutil.transform_position(hit[0], obj.matrix_world)
                dist = (pos - wp).length
                if min_dist > dist:
                    min_dist = dist
                    location = wp
                    normal = pqutil.transform_normal(hit[1], obj.matrix_world)
                    index =  hit[2] + obj.pass_index * 10000000
        return location, normal, index
